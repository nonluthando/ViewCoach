import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .forms import QUESTION_FORM_BY_TYPE
from .models import Question

TYPE_BY_SLUG = {
    "technical": Question.Type.TECHNICAL,
    "behavioural": Question.Type.BEHAVIOURAL,
    "debug": Question.Type.DEBUG,
}


def _owned_questions(user):
    return Question.objects.filter(owner=user).select_related(
        "technicalquestion",
        "behaviouralquestion",
        "debugquestion",
    )


def _question_type_from_slug(question_type_slug: str) -> str:
    try:
        return TYPE_BY_SLUG[question_type_slug]
    except KeyError as exc:
        raise Http404("Unknown question type") from exc


@login_required
def question_list(request):
    questions = _owned_questions(request.user)

    search_term = request.GET.get("q", "").strip()
    question_type = request.GET.get("type", "").strip()
    difficulty = request.GET.get("difficulty", "").strip()
    status = request.GET.get("status", "").strip()

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
            },
        },
    )


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
    question = get_object_or_404(_owned_questions(request.user), pk=pk)
    specific = question.specific
    template_by_type = {
        Question.Type.TECHNICAL: "questions/technical_question_detail.html",
        Question.Type.BEHAVIOURAL: "questions/behavioural_question_detail.html",
        Question.Type.DEBUG: "questions/debug_question_detail.html",
    }
    template_name = template_by_type.get(question.question_type)
    if not template_name or specific is question:
        raise Http404("Question details are unavailable")

    return render(
        request,
        template_name,
        {"question": question, "specific": specific},
    )


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
            form.save()
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
