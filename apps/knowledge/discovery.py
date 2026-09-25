"""Auto-generate SYSTEM knowledge documents from live Django form definitions.

Hand-written Markdown under ``knowledge_docs/`` is the reliable core of the
knowledge base. This module complements it by turning already-maintained,
user-facing copy — form field labels and ``help_text`` — into searchable
documents, so the Help Assistant stays current with the app's actual forms
without anyone hand-writing (and forgetting to update) a second copy of that
copy. It only reads form *definitions*; it never touches user data.

Only forms explicitly listed in ``FORM_SOURCES`` are included. This is a
deliberate allowlist, not automatic discovery of every form in the project —
internal/admin forms and anything not meant to explain a feature to a user
should not end up in the assistant's index.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module


@dataclass(frozen=True, slots=True)
class FormSource:
    dotted_path: str  # "apps.evidence.forms.EvidenceItemForm"
    title: str
    intro: str
    nav_hint: str  # where in the app this form lives, for the assistant to cite


FORM_SOURCES: tuple[FormSource, ...] = (
    FormSource(
        dotted_path="apps.evidence.forms.EvidenceItemForm",
        title="Logging evidence in the Evidence Bag",
        intro=(
            "The Evidence Bag records real work — projects, roles, incidents — that backs "
            "up interview answers. Each evidence item captures the following fields."
        ),
        nav_hint="Sidebar → Prove → Evidence Bag → Add evidence",
    ),
    FormSource(
        dotted_path="apps.evidence.forms.ProjectExplanationForm",
        title="Explaining a project in the Evidence Bag",
        intro=(
            "A project explanation turns one piece of evidence into a rehearsed technical "
            "walkthrough, from a 30-second pitch up to likely follow-up questions."
        ),
        nav_hint="Sidebar → Prove → Evidence Bag → open an evidence item → Explain this project",
    ),
    FormSource(
        dotted_path="apps.evidence.forms.BehaviouralStoryForm",
        title="Writing a behavioural (STAR) story",
        intro=(
            "Behavioural stories use the situation / task / action / result structure to turn "
            "evidence into an answer for behavioural interview questions."
        ),
        nav_hint="Sidebar → Prove → Evidence Bag → Behavioural stories",
    ),
    FormSource(
        dotted_path="apps.goals.forms.InterviewGoalForm",
        title="Setting an interview goal",
        intro=(
            "An interview goal connects preparation to a specific role or opportunity and "
            "drives roadmap ordering and planner scoring."
        ),
        nav_hint="Sidebar → Dashboard → Interview readiness → Create interview goal",
    ),
    FormSource(
        dotted_path="apps.planner.forms.StudyPlanPreferencesForm",
        title="Generating today's plan",
        intro=(
            "The Daily Plan turns available study time into a scored, ordered set of "
            "preparation blocks for today."
        ),
        nav_hint="Sidebar → Plan → Daily Plan",
    ),
    FormSource(
        dotted_path="apps.interviews.forms.MockInterviewCreateForm",
        title="Starting a mock interview",
        intro="A mock interview is a timed practice session in the Interview Hub.",
        nav_hint="Sidebar → Prove → Interview Hub → Start a mock interview",
    ),
    FormSource(
        dotted_path="apps.interviews.forms.MockInterviewResponseForm",
        title="Answering during a mock interview",
        intro="Each mock interview question is answered and self-assessed with these fields.",
        nav_hint="Sidebar → Prove → Interview Hub → during an active session",
    ),
    FormSource(
        dotted_path="apps.questions.forms.UserQuestionNoteForm",
        title="Adding notes to a review question",
        intro=(
            "A question only enters spaced review once it has useful notes attached — this "
            "is where those notes are written."
        ),
        nav_hint="Sidebar → Build → Reviews → open a question → Add notes",
    ),
    FormSource(
        dotted_path="apps.accounts.forms.NeedTypePreferencesForm",
        title="Setting preparation preferences",
        intro=(
            "Preparation preferences tell ViewCoach what kind of readiness the user is "
            "primarily building toward, which the planner uses to favour relevant question "
            "types."
        ),
        nav_hint="Sidebar → Settings → Preparation preferences",
    ),
)


def _load_form_class(dotted_path: str):
    module_path, _, class_name = dotted_path.rpartition(".")
    module = import_module(module_path)
    return getattr(module, class_name)


def _field_lines(form) -> list[str]:
    lines = []
    for name, field in form.fields.items():
        label = field.label or name.replace("_", " ").capitalize()
        required = "required" if field.required else "optional"
        line = f"- **{label}** ({required})"
        if field.help_text:
            line += f": {field.help_text}"
        lines.append(line)
    return lines


def build_form_document_markdown(source: FormSource) -> str:
    """Render a form's field labels and help_text as trusted Markdown."""
    form_class = _load_form_class(source.dotted_path)
    form = form_class()

    lines = [f"# {source.title}", "", source.intro, "", f"Found at: {source.nav_hint}.", ""]
    field_lines = _field_lines(form)
    if field_lines:
        lines.append("## Fields")
        lines.append("")
        lines.extend(field_lines)
    return "\n".join(lines)


def discover_form_documents() -> list[tuple[str, str, str]]:
    """Return (source_path, title, markdown) for every registered form source.

    ``source_path`` is a stable synthetic key (not a real file) used the same
    way a Markdown file's relative path is used by ``ingest_knowledge`` — as
    the upsert key for ``KnowledgeDocument.source_path``.
    """
    documents = []
    for source in FORM_SOURCES:
        markdown = build_form_document_markdown(source)
        source_path = f"generated://forms/{source.dotted_path}"
        documents.append((source_path, source.title, markdown))
    return documents
