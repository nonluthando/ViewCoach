import csv
import io
import re
from pathlib import Path

from django.db import transaction
from django.utils import timezone
from docx import Document
from pypdf import PdfReader

from .models import (
    BehaviouralQuestion,
    DebugQuestion,
    Question,
    QuestionImportBatch,
    QuestionImportItem,
    TechnicalQuestion,
)

MAX_QUESTIONS_PER_IMPORT = 200
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.*)$")
NUMBERING_PREFIX_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+")
QUESTION_COLUMN_NAMES = {
    "question",
    "questions",
    "prompt",
    "problem",
    "problem_statement",
    "problem statement",
    "text",
}


class ImportExtractionError(ValueError):
    pass


def normalize_question_text(value):
    value = NUMBERING_PREFIX_RE.sub("", value or "")
    value = MARKDOWN_HEADING_RE.sub("", value)
    return re.sub(r"\s+", " ", value).strip().casefold()


def generate_question_title(question_text):
    clean_text = re.sub(r"\s+", " ", question_text).strip()
    clean_text = NUMBERING_PREFIX_RE.sub("", clean_text)
    clean_text = MARKDOWN_HEADING_RE.sub("", clean_text)
    clean_text = clean_text.rstrip(" ?:.—-")

    words = clean_text.split()
    if not words:
        return "Untitled question"

    title = " ".join(words[:10])
    if len(words) > 10:
        title += "…"
    return title[:180]


def _clean_extracted_entry(entry):
    entry = entry.replace("\u00a0", " ").strip()
    entry = NUMBERING_PREFIX_RE.sub("", entry)
    entry = MARKDOWN_HEADING_RE.sub("", entry)
    return re.sub(r"[ \t]+", " ", entry).strip()


def extract_questions_from_plain_text(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []

    lines = text.split("\n")
    items = []
    current = []
    saw_list_marker = False

    for raw_line in lines:
        line = raw_line.strip()
        marker = LIST_ITEM_RE.match(line)
        if marker:
            saw_list_marker = True
            if current:
                items.append("\n".join(current))
            current = [marker.group(1).strip()]
            continue

        if saw_list_marker:
            if line:
                current.append(line)
            continue

    if saw_list_marker:
        if current:
            items.append("\n".join(current))
    else:
        blocks = re.split(r"\n\s*\n+", text)
        if len(blocks) > 1:
            items = blocks
        else:
            non_empty_lines = [line.strip() for line in lines if line.strip()]
            items = non_empty_lines if len(non_empty_lines) > 1 else [text]

    cleaned = [_clean_extracted_entry(item) for item in items]
    return [item for item in cleaned if item]


def _decode_text_file(file_obj):
    raw = file_obj.read()
    if isinstance(raw, str):
        return raw

    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportExtractionError("The file is not valid UTF-8 text.")


def extract_questions_from_csv(file_obj):
    text = _decode_text_file(file_obj)
    if not text.strip():
        return []

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel

    rows = list(csv.reader(io.StringIO(text), dialect=dialect))
    rows = [[cell.strip() for cell in row] for row in rows if any(cell.strip() for cell in row)]
    if not rows:
        return []

    first_row_normalized = [cell.casefold() for cell in rows[0]]
    question_column_index = next(
        (
            index
            for index, name in enumerate(first_row_normalized)
            if name in QUESTION_COLUMN_NAMES
        ),
        None,
    )

    start_index = 1 if question_column_index is not None else 0
    if question_column_index is None:
        question_column_index = 0

    questions = []
    for row in rows[start_index:]:
        if question_column_index < len(row) and row[question_column_index]:
            questions.append(row[question_column_index])
        else:
            first_value = next((cell for cell in row if cell), "")
            if first_value:
                questions.append(first_value)

    return [_clean_extracted_entry(question) for question in questions if question.strip()]


def extract_questions_from_docx(file_obj):
    try:
        document = Document(file_obj)
    except Exception as exc:
        raise ImportExtractionError("The DOCX file could not be read.") from exc

    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs]
    text = "\n".join(paragraph for paragraph in paragraphs if paragraph)
    return extract_questions_from_plain_text(text)


def extract_questions_from_pdf(file_obj):
    try:
        reader = PdfReader(file_obj)
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception as exc:
        raise ImportExtractionError("The PDF could not be read.") from exc

    text = "\n\n".join(page for page in pages if page)
    if not text.strip():
        raise ImportExtractionError(
            "No readable text was found. Scanned PDFs are not supported yet."
        )
    return extract_questions_from_plain_text(text)


def _source_type_for_filename(filename):
    suffix = Path(filename).suffix.lower()
    mapping = {
        ".txt": QuestionImportBatch.SourceType.TXT,
        ".md": QuestionImportBatch.SourceType.MARKDOWN,
        ".markdown": QuestionImportBatch.SourceType.MARKDOWN,
        ".csv": QuestionImportBatch.SourceType.CSV,
        ".docx": QuestionImportBatch.SourceType.DOCX,
        ".pdf": QuestionImportBatch.SourceType.PDF,
    }
    try:
        return mapping[suffix]
    except KeyError as exc:
        raise ImportExtractionError("Unsupported question import file type.") from exc


def extract_questions_for_batch(batch):
    if batch.source_type == QuestionImportBatch.SourceType.PASTE:
        return extract_questions_from_plain_text(batch.source_text)

    if not batch.temporary_file:
        raise ImportExtractionError("The uploaded file is no longer available.")

    batch.temporary_file.open("rb")
    try:
        if batch.source_type in {
            QuestionImportBatch.SourceType.TXT,
            QuestionImportBatch.SourceType.MARKDOWN,
        }:
            return extract_questions_from_plain_text(
                _decode_text_file(batch.temporary_file.file)
            )
        if batch.source_type == QuestionImportBatch.SourceType.CSV:
            return extract_questions_from_csv(batch.temporary_file.file)
        if batch.source_type == QuestionImportBatch.SourceType.DOCX:
            return extract_questions_from_docx(batch.temporary_file.file)
        if batch.source_type == QuestionImportBatch.SourceType.PDF:
            return extract_questions_from_pdf(batch.temporary_file.file)
    finally:
        batch.temporary_file.close()

    raise ImportExtractionError("Unsupported question import source.")


def refresh_batch_duplicates(batch):
    existing_prompts = Question.objects.filter(owner=batch.owner).values_list(
        "prompt", flat=True
    )
    existing_normalized = {normalize_question_text(prompt) for prompt in existing_prompts}
    seen_in_batch = set()

    items = list(batch.items.order_by("position"))
    changed_items = []
    for item in items:
        normalized = normalize_question_text(item.question_text)
        duplicate_reason = ""

        if not normalized:
            duplicate_reason = "Question text is empty."
        elif normalized in existing_normalized:
            duplicate_reason = "Already exists in your question library."
        elif normalized in seen_in_batch:
            duplicate_reason = "Duplicate within this import batch."

        item.normalized_text = normalized
        item.duplicate_reason = duplicate_reason
        if duplicate_reason:
            item.is_included = False
        else:
            seen_in_batch.add(normalized)

        changed_items.append(item)

    if changed_items:
        QuestionImportItem.objects.bulk_update(
            changed_items,
            ["normalized_text", "duplicate_reason", "is_included", "updated_at"],
        )
    return changed_items


def create_import_batch(*, owner, default_question_type, paste_text="", upload=None):
    if upload is not None:
        source_type = _source_type_for_filename(upload.name)
        source_filename = Path(upload.name).name
    else:
        source_type = QuestionImportBatch.SourceType.PASTE
        source_filename = ""

    batch = QuestionImportBatch.objects.create(
        owner=owner,
        source_type=source_type,
        source_filename=source_filename,
        default_question_type=default_question_type,
        temporary_file=upload,
        source_text=paste_text,
    )

    try:
        extracted_questions = extract_questions_for_batch(batch)
        extracted_questions = [question for question in extracted_questions if question.strip()]
        if not extracted_questions:
            raise ImportExtractionError("No questions could be extracted from this source.")
        if len(extracted_questions) > MAX_QUESTIONS_PER_IMPORT:
            raise ImportExtractionError(
                f"This import contains more than {MAX_QUESTIONS_PER_IMPORT} questions."
            )

        items = [
            QuestionImportItem(
                batch=batch,
                position=position,
                generated_title=generate_question_title(question_text),
                question_text=question_text,
                normalized_text=normalize_question_text(question_text),
                question_type=default_question_type,
            )
            for position, question_text in enumerate(extracted_questions, start=1)
        ]
        QuestionImportItem.objects.bulk_create(items)
        refresh_batch_duplicates(batch)

        batch.status = QuestionImportBatch.Status.READY_FOR_REVIEW
        batch.failure_message = ""
        batch.save(update_fields=["status", "failure_message", "updated_at"])
    except ImportExtractionError as exc:
        batch.status = QuestionImportBatch.Status.FAILED
        batch.failure_message = str(exc)
        batch.save(update_fields=["status", "failure_message", "updated_at"])

    return batch


def _create_question_from_item(item, batch):
    common_fields = {
        "owner": batch.owner,
        "import_batch": batch,
        "title": item.generated_title,
        "prompt": item.question_text,
        "status": Question.Status.NEEDS_NOTES,
    }

    if item.question_type == Question.Type.TECHNICAL:
        return TechnicalQuestion.objects.create(**common_fields)
    if item.question_type == Question.Type.BEHAVIOURAL:
        return BehaviouralQuestion.objects.create(**common_fields)
    if item.question_type == Question.Type.DEBUG:
        return DebugQuestion.objects.create(**common_fields)
    raise ImportExtractionError("An import item has an unsupported question type.")


def confirm_import_batch(*, batch_id, owner, confirmation_token):
    file_name_to_delete = ""
    file_storage = None

    with transaction.atomic():
        batch = (
            QuestionImportBatch.objects.select_for_update()
            .filter(owner=owner)
            .get(pk=batch_id)
        )

        if str(batch.idempotency_key) != str(confirmation_token):
            raise ImportExtractionError("This import confirmation could not be verified.")

        if batch.status in {
            QuestionImportBatch.Status.IMPORTED,
            QuestionImportBatch.Status.ARCHIVED,
        }:
            return batch, False

        if batch.status not in {
            QuestionImportBatch.Status.DRAFT,
            QuestionImportBatch.Status.READY_FOR_REVIEW,
        }:
            raise ImportExtractionError("This batch is not ready to be imported.")

        refresh_batch_duplicates(batch)
        items = list(
            batch.items.filter(is_included=True, duplicate_reason="").order_by("position")
        )
        if not items:
            raise ImportExtractionError("Select at least one non-duplicate question.")

        batch.status = QuestionImportBatch.Status.IMPORTING
        batch.save(update_fields=["status", "updated_at"])

        for item in items:
            _create_question_from_item(item, batch)

        file_name_to_delete = batch.temporary_file.name
        file_storage = batch.temporary_file.storage if file_name_to_delete else None

        batch.items.all().delete()
        batch.source_text = ""
        batch.temporary_file = ""
        batch.status = QuestionImportBatch.Status.IMPORTED
        batch.created_question_count = len(items)
        batch.imported_at = timezone.now()
        batch.failure_message = ""
        batch.save(
            update_fields=[
                "source_text",
                "temporary_file",
                "status",
                "created_question_count",
                "imported_at",
                "failure_message",
                "updated_at",
            ]
        )

        if file_storage and file_name_to_delete:
            transaction.on_commit(lambda: file_storage.delete(file_name_to_delete))

    return batch, True
