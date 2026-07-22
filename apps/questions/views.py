import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    QUESTION_FORM_BY_TYPE,
    QuestionImportItemFormSet,
    QuestionImportStartForm,
    UserQuestionNoteForm,
)
from .importing import (
    ImportExtractionError,
    confirm_import_batch,
    create_import_batch,
    refresh_batch_duplicates,
)
from .models import Question, QuestionImportBatch, UserQuestionNote, UserQuestionState

TYPE_BY_SLUG = {
    "technical": Question.Type.TECHNICAL,
    "concept": Question.Type.CONCEPT,
    "behavioural": Question.Type.BEHAVIOURAL,
    "debug": Question.Type.DEBUG,
}


def _question_queryset():
    return Question.objects.select_related(
        "technicalquestion",
        "conceptquestion",
        "behaviouralquestion",
        "debugquestion",
        "import_batch",
    )


def _accessible_questions(user):
    return _question_queryset().filter(Q(owner=user) | Q(is_system=True))


def _owned_questions(user):
    return _question_queryset().filter(owner=user, is_system=False)


def _owned_batches(user):
    return QuestionImportBatch.objects.filter(owner=user)


def _question_type_from_slug(question_type_slug: str) -> str:
    try:
        return TYPE_BY_SLUG[question_type_slug]
    except KeyError as exc:
        raise Http404("Unknown question type") from exc


@login_required
def question_list(request):
    questions = _accessible_questions(request.user)

    search_term = request.GET.get("q", "").strip()
    question_type = request.GET.get("type", "").strip()
    difficulty = request.GET.get("difficulty", "").strip()
    status = request.GET.get("status", "").strip()
    source = request.GET.get("source", "").strip()

    if search_term:
        questions = questions.filter(
            Q(title__icontains=search_term)
            | Q(prompt__icontains=search_term)
            | Q(company__icontains=search_term)
            | Q(technicalquestion__topic__icontains=search_term)
            | Q(technicalquestion__pattern__icontains=search_term)
            | Q(technicalquestion__first_hint__icontains=search_term)
            | Q(technicalquestion__intuition__icontains=search_term)
            | Q(technicalquestion__optimal_approach__icontains=search_term)
            | Q(technicalquestion__mistakes__icontains=search_term)
            | Q(conceptquestion__canonical_answer__icontains=search_term)
            | Q(conceptquestion__category__icontains=search_term)
            | Q(behaviouralquestion__leadership_principles__icontains=search_term)
            | Q(behaviouralquestion__stories__icontains=search_term)
            | Q(debugquestion__repository__icontains=search_term)
        ).distinct()

    valid_types = {choice for choice, _ in Question.Type.choices}
    valid_difficulties = {choice for choice, _ in Question.Difficulty.choices}
    valid_statuses = {choice for choice, _ in Question.Status.choices}

    if question_type in valid_types:
        questions = questions.filter(question_type=question_type)
    if difficulty in valid_difficulties:
        questions = questions.filter(difficulty=difficulty)
    if status in valid_statuses:
        questions = questions.filter(status=status)
    if source == "built_in":
        questions = questions.filter(is_system=True)
    elif source == "mine":
        questions = questions.filter(owner=request.user, is_system=False)

    paginator = Paginator(questions, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "questions/question_list.html",
        {
            "page": page,
            "question_types": Question.Type.choices,
            "difficulties": Question.Difficulty.choices,
            "statuses": Question.Status.choices,
            "filters": {
                "q": search_term,
                "type": question_type,
                "difficulty": difficulty,
                "status": status,
                "source": source,
            },
        },
    )


@login_required
@require_POST
def bulk_mark_ready(request):
    selected_ids = request.POST.getlist("selected_questions")
    questions = list(_owned_questions(request.user).filter(pk__in=selected_ids))

    if not selected_ids:
        messages.info(request, "Select at least one question.")
        return redirect("questions:list")

    ready_count = 0
    skipped = []
    for question in questions:
        try:
            question.mark_ready()
            ready_count += 1
        except ValidationError:
            skipped.append(
                f"{question.title}: missing {', '.join(question.readiness_errors())}."
            )

    if ready_count:
        messages.success(
            request,
            f"{ready_count} question{'s' if ready_count != 1 else ''} marked ready.",
        )
    for reason in skipped:
        messages.warning(request, reason)

    return redirect("questions:list")


@login_required
def choose_question_type(request):
    return render(request, "questions/choose_question_type.html")


@login_required
def question_create(request, question_type_slug):
    question_type = _question_type_from_slug(question_type_slug)
    form_class = QUESTION_FORM_BY_TYPE[question_type]

    if request.method == "POST":
        form = form_class(request.POST)
        submission_token = request.POST.get("submission_token", "")

        if form.is_valid():
            try:
                creation_token = uuid.UUID(submission_token)
            except (AttributeError, TypeError, ValueError):
                form.add_error(
                    None,
                    "This form could not be verified. Refresh the page and try again.",
                )
            else:
                question = form.save(commit=False)
                question.owner = request.user
                question.creation_token = creation_token
                question.status = Question.Status.NEEDS_NOTES

                try:
                    with transaction.atomic():
                        question.save()
                except IntegrityError:
                    existing_question = Question.objects.filter(
                        owner=request.user,
                        creation_token=creation_token,
                    ).first()
                    if existing_question is None:
                        raise

                    messages.info(request, "That question was already added.")
                    return redirect("questions:detail", pk=existing_question.pk)

                messages.success(request, "Question added to your library.")
                return redirect("questions:detail", pk=question.pk)
    else:
        form = form_class()
        submission_token = str(uuid.uuid4())

    return render(
        request,
        "questions/question_form.html",
        {
            "form": form,
            "question_type_label": Question.Type(question_type).label,
            "is_editing": False,
            "submission_token": submission_token,
        },
    )


@login_required
def question_detail(request, pk):
    question = get_object_or_404(_accessible_questions(request.user), pk=pk)
    specific = question.specific
    state = UserQuestionState.objects.filter(user=request.user, question=question).first()
    note = UserQuestionNote.objects.filter(user=request.user, question=question).first()
    template_by_type = {
        Question.Type.TECHNICAL: "questions/technical_question_detail.html",
        Question.Type.CONCEPT: "questions/concept_question_detail.html",
        Question.Type.BEHAVIOURAL: "questions/behavioural_question_detail.html",
        Question.Type.DEBUG: "questions/debug_question_detail.html",
    }
    template_name = template_by_type.get(question.question_type)
    if not template_name or specific is question:
        raise Http404("Question details are unavailable")

    return render(
        request,
        template_name,
        {
            "question": question,
            "specific": specific,
            "readiness_errors": question.readiness_errors(),
            "user_state": state,
            "user_note": note,
        },
    )


@login_required
@require_POST
def question_mark_ready(request, pk):
    question = get_object_or_404(_owned_questions(request.user), pk=pk)
    try:
        question.mark_ready()
    except ValidationError:
        messages.warning(
            request,
            f"Add {', '.join(question.readiness_errors())} before marking this question ready.",
        )
    else:
        messages.success(request, "Question marked ready for review.")
    return redirect("questions:detail", pk=question.pk)


@login_required
def question_edit(request, pk):
    question = get_object_or_404(_owned_questions(request.user), pk=pk)
    specific = question.specific
    if specific is question:
        raise Http404("Question details are unavailable")

    form_class = QUESTION_FORM_BY_TYPE[question.question_type]
    if request.method == "POST":
        form = form_class(request.POST, instance=specific)
        if form.is_valid():
            updated_question = form.save()
            updated_question.ensure_valid_readiness_status()
            messages.success(request, "Question updated.")
            return redirect("questions:detail", pk=question.pk)
    else:
        form = form_class(instance=specific)

    return render(
        request,
        "questions/question_form.html",
        {
            "form": form,
            "question": question,
            "question_type_label": question.get_question_type_display(),
            "is_editing": True,
        },
    )


@login_required
def question_delete(request, pk):
    question = get_object_or_404(_owned_questions(request.user), pk=pk)

    if request.method == "POST":
        title = question.title
        question.delete()
        messages.success(request, f'“{title}” was deleted.')
        return redirect("questions:list")

    return render(request, "questions/question_confirm_delete.html", {"question": question})


@login_required
def question_notes(request, pk):
    question = get_object_or_404(_accessible_questions(request.user), pk=pk)
    note, _ = UserQuestionNote.objects.get_or_create(user=request.user, question=question)
    state, _ = UserQuestionState.objects.get_or_create(user=request.user, question=question)

    if request.method == "POST":
        form = UserQuestionNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            state.mark_in_progress()
            state.save()
            messages.success(request, "Your notes were saved.")
            return redirect("questions:detail", pk=question.pk)
    else:
        form = UserQuestionNoteForm(instance=note)

    return render(
        request,
        "questions/question_notes_form.html",
        {"question": question, "form": form},
    )


@login_required
@require_POST
def question_toggle_bookmark(request, pk):
    question = get_object_or_404(_accessible_questions(request.user), pk=pk)
    state, _ = UserQuestionState.objects.get_or_create(user=request.user, question=question)
    state.bookmarked = not state.bookmarked
    state.save(update_fields=["bookmarked", "updated_at"])
    messages.success(request, "Saved to your library." if state.bookmarked else "Removed from saved questions.")
    return redirect("questions:detail", pk=question.pk)


@login_required
def question_import_start(request):
    if request.method == "POST":
        form = QuestionImportStartForm(request.POST, request.FILES)
        if form.is_valid():
            batch = create_import_batch(
                owner=request.user,
                default_question_type=form.cleaned_data["default_question_type"],
                paste_text=form.cleaned_data["paste_text"],
                upload=form.cleaned_data["upload"],
            )
            if batch.status == QuestionImportBatch.Status.FAILED:
                messages.warning(request, batch.failure_message)
            else:
                messages.success(
                    request,
                    f"Extracted {batch.items.count()} questions. Review them before importing.",
                )
            return redirect("questions:import_batch", batch_id=batch.pk)
    else:
        form = QuestionImportStartForm()

    return render(request, "questions/import_start.html", {"form": form})


@login_required
def question_import_batch(request, batch_id):
    batch = get_object_or_404(_owned_batches(request.user), pk=batch_id)

    if batch.status in {
        QuestionImportBatch.Status.IMPORTED,
        QuestionImportBatch.Status.ARCHIVED,
    }:
        return render(
            request,
            "questions/import_batch.html",
            {"batch": batch, "created_questions": batch.created_questions.all()},
        )

    if batch.status == QuestionImportBatch.Status.FAILED:
        return render(request, "questions/import_batch.html", {"batch": batch})

    queryset = batch.items.order_by("position")
    if request.method == "POST":
        formset = QuestionImportItemFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            with transaction.atomic():
                formset.save()
                refresh_batch_duplicates(batch)
                batch.status = QuestionImportBatch.Status.READY_FOR_REVIEW
                batch.save(update_fields=["status", "updated_at"])

            if request.POST.get("action") == "confirm":
                try:
                    batch, created = confirm_import_batch(
                        batch_id=batch.pk,
                        owner=request.user,
                        confirmation_token=request.POST.get("confirmation_token", ""),
                    )
                except ImportExtractionError as exc:
                    messages.warning(request, str(exc))
                else:
                    if created:
                        messages.success(
                            request,
                            f"Created {batch.created_question_count} questions. "
                            "Add notes when you are ready.",
                        )
                    else:
                        messages.info(request, "This batch was already imported.")
                return redirect("questions:import_batch", batch_id=batch.pk)

            messages.success(request, "Import review saved.")
            return redirect("questions:import_batch", batch_id=batch.pk)
    else:
        formset = QuestionImportItemFormSet(queryset=queryset)

    return render(
        request,
        "questions/import_batch.html",
        {"batch": batch, "formset": formset},
    )


@login_required
@require_POST
def question_import_confirm(request, batch_id):
    batch = get_object_or_404(_owned_batches(request.user), pk=batch_id)
    try:
        batch, created = confirm_import_batch(
            batch_id=batch.pk,
            owner=request.user,
            confirmation_token=request.POST.get("confirmation_token", ""),
        )
    except ImportExtractionError as exc:
        messages.warning(request, str(exc))
    else:
        if created:
            messages.success(
                request,
                f"Created {batch.created_question_count} questions. Add notes when you are ready.",
            )
        else:
            messages.info(request, "This batch was already imported.")
    return redirect("questions:import_batch", batch_id=batch.pk)


@login_required
def question_import_delete(request, batch_id):
    batch = get_object_or_404(_owned_batches(request.user), pk=batch_id)
    if not batch.can_delete:
        messages.warning(request, "Imported batches cannot be deleted. Archive them instead.")
        return redirect("questions:import_batch", batch_id=batch.pk)

    if request.method == "POST":
        if batch.temporary_file:
            batch.temporary_file.delete(save=False)
        batch.delete()
        messages.success(request, "Import batch deleted.")
        return redirect("questions:import_history")

    return render(request, "questions/import_confirm_delete.html", {"batch": batch})


@login_required
@require_POST
def question_import_archive(request, batch_id):
    batch = get_object_or_404(_owned_batches(request.user), pk=batch_id)
    if batch.status != QuestionImportBatch.Status.IMPORTED:
        messages.warning(request, "Only completed imports can be archived.")
    else:
        batch.status = QuestionImportBatch.Status.ARCHIVED
        batch.archived_at = timezone.now()
        batch.save(update_fields=["status", "archived_at", "updated_at"])
        messages.success(request, "Import batch archived.")
    return redirect("questions:import_history")


@login_required
def question_import_history(request):
    batches = _owned_batches(request.user).prefetch_related("created_questions")
    return render(request, "questions/import_history.html", {"batches": batches})
