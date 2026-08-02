#!/usr/bin/env python3
# ruff: noqa: E501
"""Apply ViewCoach Patch 3C: aim-driven daily planning and interview readiness."""

from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()


def read(path: str) -> str:
    target = ROOT / path
    if not target.exists():
        raise SystemExit(f"Missing required file: {path}")
    return target.read_text()


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)


def replace_once(path: str, old: str, new: str, label: str) -> None:
    text = read(path)
    if new in text:
        print(f"✓ Already applied: {label}")
        return
    if old not in text:
        raise SystemExit(f"Could not find marker for {label} in {path}")
    write(path, text.replace(old, new, 1))
    print(f"✓ Applied: {label}")


def replace_between(path: str, start: str, end: str, replacement: str, label: str) -> None:
    text = read(path)
    if replacement in text:
        print(f"✓ Already applied: {label}")
        return
    start_index = text.find(start)
    if start_index < 0:
        raise SystemExit(f"Could not find start marker for {label} in {path}")
    end_index = text.find(end, start_index)
    if end_index < 0:
        raise SystemExit(f"Could not find end marker for {label} in {path}")
    write(path, text[:start_index] + replacement + text[end_index:])
    print(f"✓ Applied: {label}")


def append_once(path: str, marker: str, content: str, label: str) -> None:
    text = read(path)
    if marker in text:
        print(f"✓ Already applied: {label}")
        return
    write(path, text.rstrip() + "\n\n" + content.strip() + "\n")
    print(f"✓ Applied: {label}")


def create_once(path: str, content: str, label: str) -> None:
    target = ROOT / path
    if target.exists():
        if target.read_text() == content:
            print(f"✓ Already created: {label}")
            return
        raise SystemExit(f"Refusing to overwrite existing file: {path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    print(f"✓ Created: {label}")


replace_once(
    "apps/planner/candidates.py",
    '''class CandidateKind(StrEnum):
    REVIEW = "REVIEW"
    ROADMAP = "ROADMAP"
    WEAK_AREA = "WEAK_AREA"
    PRACTICE = "PRACTICE"
    LIBRARY = "LIBRARY"
''',
    '''class CandidateKind(StrEnum):
    REVIEW = "REVIEW"
    STAR = "STAR"
    ROADMAP = "ROADMAP"
    WEAK_AREA = "WEAK_AREA"
    PRACTICE = "PRACTICE"
    EVIDENCE = "EVIDENCE"
    GUIDE = "GUIDE"
    MOCK = "MOCK"
    LIBRARY = "LIBRARY"
''',
    "planner candidate kinds",
)

replace_once(
    "apps/planner/candidates.py",
    '''    aim_alignment_explanation: str = ""

    description: str = ""
''',
    '''    aim_alignment_explanation: str = ""
    action_path: str = ""
    is_required: bool = False

    description: str = ""
''',
    "planner candidate navigation and requirement fields",
)

replace_once(
    "apps/planner/models.py",
    '''    class Kind(models.TextChoices):
        REVIEW = "REVIEW", "Due review"
        ROADMAP = "ROADMAP", "Roadmap"
        WEAK_AREA = "WEAK_AREA", "Weak area"
        PRACTICE = "PRACTICE", "Practice"
        LIBRARY = "LIBRARY", "Question library"
''',
    '''    class Kind(models.TextChoices):
        REVIEW = "REVIEW", "Due review"
        STAR = "STAR", "Daily STAR practice"
        ROADMAP = "ROADMAP", "Roadmap"
        WEAK_AREA = "WEAK_AREA", "Weak area"
        PRACTICE = "PRACTICE", "Practice"
        EVIDENCE = "EVIDENCE", "Evidence bank"
        GUIDE = "GUIDE", "Built-in guide"
        MOCK = "MOCK", "Mock interview"
        LIBRARY = "LIBRARY", "Question library"
''',
    "study recommendation kinds",
)

replace_once(
    "apps/planner/models.py",
    '''    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
''',
    '''    action_path = models.CharField(max_length=500, blank=True)
    is_required = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
''',
    "study recommendation action and required fields",
)

replace_between(
    "apps/planner/models.py",
    '''    @property
    def action_label(self):
''',
    '''    def __str__(self):
''',
    '''    @property
    def action_label(self):
        labels = {
            self.Kind.REVIEW: "Start reviews",
            self.Kind.STAR: "Open STAR practice",
            self.Kind.ROADMAP: "Open topic",
            self.Kind.WEAK_AREA: "Revisit question",
            self.Kind.PRACTICE: "Open practice question",
            self.Kind.EVIDENCE: "Open evidence bank",
            self.Kind.GUIDE: "Open guide",
            self.Kind.MOCK: "Open mock interview",
            self.Kind.LIBRARY: (
                "Open question" if self.question_id else "Open question library"
            ),
        }
        return labels[self.kind]

    @property
    def action_url(self):
        if self.action_path:
            return self.action_path

        if self.kind == self.Kind.REVIEW:
            if self.question_id:
                return reverse("reviews:review", args=[self.question_id])
            return reverse("reviews:queue")

        if self.topic_id:
            return reverse(
                "roadmaps:topic_detail",
                kwargs={
                    "slug": self.topic.section.roadmap.slug,
                    "topic_id": self.topic_id,
                },
            )

        if self.question_id:
            return reverse("questions:detail", args=[self.question_id])

        return reverse("questions:list")

''',
    "study recommendation action labels and destinations",
)

create_once(
    "apps/planner/migrations/0003_readiness_recommendations.py",
    '''from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("planner", "0002_studyplan_selection_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="studyrecommendation",
            name="action_path",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="studyrecommendation",
            name="is_required",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="studyrecommendation",
            name="kind",
            field=models.CharField(
                choices=[
                    ("REVIEW", "Due review"),
                    ("STAR", "Daily STAR practice"),
                    ("ROADMAP", "Roadmap"),
                    ("WEAK_AREA", "Weak area"),
                    ("PRACTICE", "Practice"),
                    ("EVIDENCE", "Evidence bank"),
                    ("GUIDE", "Built-in guide"),
                    ("MOCK", "Mock interview"),
                    ("LIBRARY", "Question library"),
                ],
                max_length=16,
            ),
        ),
    ]
''',
    "planner readiness migration",
)

replace_between(
    "apps/planner/scoring.py",
    '''BASE_SCORE_BY_KIND = {
''',
    '''

@dataclass(frozen=True, slots=True)
class ScoreComponent:
''',
    '''BASE_SCORE_BY_KIND = {
    CandidateKind.REVIEW: 100,
    CandidateKind.STAR: 95,
    CandidateKind.ROADMAP: 80,
    CandidateKind.WEAK_AREA: 70,
    CandidateKind.EVIDENCE: 65,
    CandidateKind.MOCK: 65,
    CandidateKind.GUIDE: 55,
    CandidateKind.PRACTICE: 50,
    CandidateKind.LIBRARY: 20,
}

KIND_ORDER = {
    CandidateKind.REVIEW: 0,
    CandidateKind.STAR: 1,
    CandidateKind.ROADMAP: 2,
    CandidateKind.WEAK_AREA: 3,
    CandidateKind.PRACTICE: 4,
    CandidateKind.EVIDENCE: 5,
    CandidateKind.GUIDE: 6,
    CandidateKind.MOCK: 7,
    CandidateKind.LIBRARY: 8,
}

''',
    "readiness candidate scores and ordering",
)

replace_once(
    "apps/planner/scoring.py",
    '''                CandidateKind.REVIEW: "Due review work receives first priority.",
                CandidateKind.ROADMAP: "Focused roadmap learning advances active study.",
                CandidateKind.WEAK_AREA: "Recent difficulty makes this useful recovery work.",
                CandidateKind.PRACTICE: "Fresh practice strengthens retrieval and application.",
                CandidateKind.LIBRARY: "Library preparation supports later study sessions.",
''',
    '''                CandidateKind.REVIEW: "Due review work receives first priority.",
                CandidateKind.STAR: (
                    "Daily STAR practice keeps behavioural preparation active."
                ),
                CandidateKind.ROADMAP: (
                    "Focused roadmap learning advances active study."
                ),
                CandidateKind.WEAK_AREA: (
                    "Recent difficulty makes this useful recovery work."
                ),
                CandidateKind.PRACTICE: (
                    "Fresh practice strengthens retrieval and application."
                ),
                CandidateKind.EVIDENCE: (
                    "A stronger evidence bank improves interview answers."
                ),
                CandidateKind.GUIDE: (
                    "A built-in guide closes a preparation knowledge gap."
                ),
                CandidateKind.MOCK: (
                    "Mock practice turns preparation into interview performance."
                ),
                CandidateKind.LIBRARY: (
                    "Library preparation supports later study sessions."
                ),
''',
    "readiness score explanations",
)

replace_between(
    "apps/accounts/needs.py",
    '''NEED_KIND_BONUSES = {
''',
    '''


def need_type_experience''',
    '''NEED_KIND_BONUSES = {
    User.NeedType.LEARN_ORGANISE: {
        "ROADMAP": 30,
        "LIBRARY": 20,
        "GUIDE": 5,
    },
    User.NeedType.PRACTISE_RETAIN: {
        "REVIEW": 15,
        "WEAK_AREA": 30,
        "PRACTICE": 35,
        "LIBRARY": 20,
    },
    User.NeedType.INTERVIEW_SKILLS: {
        "REVIEW": 10,
        "STAR": 40,
        "EVIDENCE": 35,
        "GUIDE": 25,
        "MOCK": 35,
        "PRACTICE": 20,
    },
}
''',
    "aim-specific planner weights",
)

replace_once(
    "apps/planner/policies.py",
    '''WEAK_AREA_BLOCK_MINUTES = 15
''',
    '''WEAK_AREA_BLOCK_MINUTES = 15
STAR_BLOCK_MINUTES = 15
READINESS_BLOCK_MINUTES = 20
''',
    "readiness block durations",
)

replace_once(
    "apps/planner/policies.py",
    '''    max_weak_area_blocks: int
''',
    '''    max_weak_area_blocks: int
    max_readiness_blocks: int = 0
''',
    "readiness policy limit",
)

# Replace the final policy function as one unit.
policies_path = ROOT / "apps/planner/policies.py"
policies_text = policies_path.read_text()
new_policy_marker = "def _need_adjusted_roadmap_limit"
if new_policy_marker not in policies_text:
    old_start = policies_text.find("def plan_policy_for_budget(*, time_budget_minutes, due_count):")
    if old_start < 0:
        raise SystemExit("Could not find the old plan_policy_for_budget implementation.")
    replacement = '''def _need_adjusted_roadmap_limit(*, limit, budget, primary_need_type):
    if primary_need_type == "PRACTISE_RETAIN":
        return min(limit, 1 if budget < 240 else 2)
    if primary_need_type == "INTERVIEW_SKILLS":
        return min(limit, 1 if budget < 180 else 2)
    return limit


def _need_adjusted_practice_minutes(*, minutes, budget, primary_need_type):
    if budget < 30:
        return 0
    if primary_need_type == "PRACTISE_RETAIN":
        return max(minutes, _round_down_to_five(budget * 40 // 100))
    if primary_need_type == "INTERVIEW_SKILLS":
        return max(minutes, _round_down_to_five(budget * 25 // 100))
    if primary_need_type == "LEARN_ORGANISE":
        learning_ceiling = max(15, _round_down_to_five(budget * 15 // 100))
        return min(minutes, learning_ceiling)
    return minutes


def plan_policy_for_budget(
    *,
    time_budget_minutes,
    due_count,
    primary_need_type="",
    secondary_need_type="",
):
    budget = max(1, int(time_budget_minutes))
    review_target = _review_target_minutes(
        time_budget_minutes=budget,
        due_count=max(0, due_count),
    )
    minutes_after_review = max(0, budget - review_target)

    band_roadmap_limit = _roadmap_limit_for_budget(budget)
    band_roadmap_limit = _need_adjusted_roadmap_limit(
        limit=band_roadmap_limit,
        budget=budget,
        primary_need_type=primary_need_type,
    )
    roadmap_limit_that_fits = min(
        band_roadmap_limit,
        minutes_after_review // ROADMAP_BLOCK_MINUTES,
    )
    minimum_learning_minutes = roadmap_limit_that_fits * ROADMAP_BLOCK_MINUTES

    desired_practice = _desired_practice_minutes(budget)
    desired_practice = _need_adjusted_practice_minutes(
        minutes=desired_practice,
        budget=budget,
        primary_need_type=primary_need_type,
    )
    practice_room = max(0, minutes_after_review - minimum_learning_minutes)
    practice_target = min(desired_practice, practice_room)

    if budget < 120:
        max_practice_blocks = 1
    elif budget < 360:
        max_practice_blocks = 2
    else:
        max_practice_blocks = 3

    interview_is_selected = "INTERVIEW_SKILLS" in {
        primary_need_type,
        secondary_need_type,
    }
    if budget < 30:
        max_readiness_blocks = 0
    elif primary_need_type == "INTERVIEW_SKILLS" and budget >= 90:
        max_readiness_blocks = 2
    elif interview_is_selected or budget >= 60:
        max_readiness_blocks = 1
    else:
        max_readiness_blocks = 0

    return DailyPlanPolicy(
        time_budget_minutes=budget,
        review_target_minutes=review_target,
        max_roadmaps=roadmap_limit_that_fits,
        max_topics_per_roadmap=(MAX_TOPICS_PER_ROADMAP if budget >= 240 else 1),
        practice_target_minutes=practice_target,
        max_practice_blocks=max_practice_blocks,
        max_weak_area_blocks=2 if budget >= 240 else 1,
        max_readiness_blocks=max_readiness_blocks,
    )
'''
    policies_path.write_text(policies_text[:old_start] + replacement)
    print("✓ Applied: aim-adjusted daily plan policy")

replace_once(
    "apps/planner/candidate_builders.py",
    '''from django.utils import timezone
''',
    '''from django.urls import reverse
from django.utils import timezone
''',
    "planner reverse import",
)

replace_once(
    "apps/planner/candidate_builders.py",
    '''from apps.goals.models import InterviewGoal
''',
    '''from apps.evidence.models import BehaviouralStory, EvidenceItem
from apps.goals.models import InterviewGoal
from apps.interviews.models import MockInterview
''',
    "readiness model imports",
)

replace_once(
    "apps/planner/candidate_builders.py",
    '''    ROADMAP_BLOCK_MINUTES,
''',
    '''    READINESS_BLOCK_MINUTES,
    ROADMAP_BLOCK_MINUTES,
''',
    "readiness policy import",
)

replace_once(
    "apps/planner/candidate_builders.py",
    '''    WEAK_AREA_BLOCK_MINUTES,
''',
    '''    STAR_BLOCK_MINUTES,
    WEAK_AREA_BLOCK_MINUTES,
''',
    "STAR policy import",
)

readiness_functions = '''def _daily_star_candidate(*, user, time_budget_minutes):
    duration = min(STAR_BLOCK_MINUTES, max(1, int(time_budget_minutes)))
    evidence_items = list(
        EvidenceItem.objects.filter(owner=user).order_by("updated_at", "pk")
    )
    stories = list(
        BehaviouralStory.objects.filter(evidence__owner=user)
        .select_related("evidence")
        .order_by("updated_at", "pk")
    )

    if not evidence_items:
        title = "Create evidence for today's STAR story"
        description = (
            "Capture one real project, work or leadership example that can "
            "become a behavioural interview story."
        )
        action_path = reverse("evidence:create")
        source = "create-evidence"
        source_ids = (user.pk,)
    elif not stories:
        title = "Create today's STAR story"
        description = (
            "Turn one evidence item into a structured situation, task, "
            "action and result answer."
        )
        action_path = reverse("evidence:behavioural_story_create")
        source = "create-story"
        source_ids = (evidence_items[0].pk,)
    else:
        story = min(
            stories,
            key=lambda item: (
                item.is_interview_ready,
                item.completed_interview_sections,
                item.updated_at,
                item.pk,
            ),
        )
        action_path = reverse(
            "evidence:behavioural_story_edit",
            args=[story.pk],
        )
        source_ids = (story.pk,)
        if story.is_interview_ready:
            title = f"Practise STAR story: {story.title}"
            description = (
                "Answer this story aloud without reading, then tighten the "
                "result and likely follow-up responses."
            )
            source = "rehearse-story"
        else:
            missing = ", ".join(story.missing_interview_sections[:2])
            title = f"Strengthen STAR story: {story.title}"
            description = (
                f"Complete the missing interview-ready sections: {missing}."
            )
            source = "strengthen-story"

    return PlanCandidate(
        candidate_id=stable_candidate_id(
            kind=CandidateKind.STAR,
            source=source,
            source_ids=source_ids,
        ),
        kind=CandidateKind.STAR,
        title=title,
        estimated_minutes=duration,
        context_key="interview:star",
        action_path=action_path,
        is_required=True,
        description=description,
        rationale=(
            "STAR practice is a daily non-negotiable so behavioural "
            "preparation cannot be postponed indefinitely."
        ),
    )


def _evidence_candidate(*, user):
    evidence_items = list(
        EvidenceItem.objects.filter(owner=user).order_by("updated_at", "pk")
    )
    if not evidence_items:
        return PlanCandidate(
            candidate_id=f"evidence:create:{user.pk}",
            kind=CandidateKind.EVIDENCE,
            title="Start your evidence bank",
            estimated_minutes=READINESS_BLOCK_MINUTES,
            context_key="interview:evidence",
            action_path=reverse("evidence:create"),
            description=(
                "Capture one project, work, coursework or leadership example "
                "with your personal contribution and outcome."
            ),
        )

    incomplete = next(
        (
            item
            for item in evidence_items
            if not item.summary.strip()
            or not item.personal_contribution.strip()
            or not item.outcomes.strip()
        ),
        None,
    )
    if incomplete is not None:
        return PlanCandidate(
            candidate_id=f"evidence:strengthen:{incomplete.pk}",
            kind=CandidateKind.EVIDENCE,
            title=f"Strengthen evidence: {incomplete.title}",
            estimated_minutes=READINESS_BLOCK_MINUTES,
            context_key="interview:evidence",
            action_path=reverse("evidence:edit", args=[incomplete.pk]),
            description=(
                "Add the missing context, personal contribution and "
                "measurable outcome so this example is interview-ready."
            ),
        )

    return PlanCandidate(
        candidate_id=f"evidence:review-pack:{user.pk}",
        kind=CandidateKind.EVIDENCE,
        title="Review your interview evidence pack",
        estimated_minutes=READINESS_BLOCK_MINUTES,
        context_key="interview:evidence",
        action_path=reverse("evidence:interview_pack"),
        description=(
            "Check that your strongest examples cover the competencies and "
            "technical decisions you are likely to discuss."
        ),
    )


def _guide_candidate(*, user, plan_date):
    guides = (
        (
            "General interview playbook",
            "Review the built-in structure for clear, evidence-based answers.",
            reverse("evidence:general_interview_playbook"),
        ),
        (
            "Responsible AI-use guide",
            "Prepare to explain how you use AI while preserving judgment and verification.",
            reverse("evidence:ai_coding_prep"),
        ),
        (
            "AI repository-task playbook",
            "Review the workflow for debugging, testing and explaining AI-assisted changes.",
            reverse("evidence:ai_repository_playbook"),
        ),
    )
    index = (plan_date.toordinal() + (user.pk or 0)) % len(guides)
    title, description, action_path = guides[index]
    return PlanCandidate(
        candidate_id=f"guide:{index}:{plan_date.isoformat()}",
        kind=CandidateKind.GUIDE,
        title=f"Review guide: {title}",
        estimated_minutes=READINESS_BLOCK_MINUTES,
        context_key="interview:guide",
        action_path=action_path,
        description=description,
    )


def _mock_candidate(*, user):
    active = (
        MockInterview.objects.filter(
            user=user,
            status__in=[
                MockInterview.Status.READY,
                MockInterview.Status.IN_PROGRESS,
            ],
        )
        .order_by("-updated_at", "-pk")
        .first()
    )
    if active is not None:
        return PlanCandidate(
            candidate_id=f"mock:continue:{active.pk}",
            kind=CandidateKind.MOCK,
            title="Continue your mock interview",
            estimated_minutes=max(15, min(30, active.duration_minutes)),
            context_key="interview:mock",
            action_path=active.get_absolute_url(),
            description=(
                "Finish the interview you already started before creating "
                "another practice session."
            ),
        )

    return PlanCandidate(
        candidate_id=f"mock:create:{user.pk}",
        kind=CandidateKind.MOCK,
        title="Run a focused mock interview",
        estimated_minutes=READINESS_BLOCK_MINUTES,
        context_key="interview:mock",
        action_path=reverse("interviews:create"),
        description=(
            "Create a short mock that turns stored knowledge and evidence "
            "into spoken interview performance."
        ),
    )


def _build_readiness_candidates(
    *,
    user,
    plan_date,
    time_budget_minutes,
    candidates,
):
    candidates.append(
        _daily_star_candidate(
            user=user,
            time_budget_minutes=time_budget_minutes,
        )
    )
    candidates.extend(
        [
            _evidence_candidate(user=user),
            _guide_candidate(user=user, plan_date=plan_date),
            _mock_candidate(user=user),
        ]
    )


'''

replace_once(
    "apps/planner/candidate_builders.py",
    '''def _build_library_candidate(
''',
    readiness_functions + '''def _build_library_candidate(
''',
    "daily STAR and readiness candidate builders",
)

replace_once(
    "apps/planner/candidate_builders.py",
    '''    if candidates:
        return
''',
    '''    content_kinds = {
        CandidateKind.REVIEW,
        CandidateKind.ROADMAP,
        CandidateKind.WEAK_AREA,
        CandidateKind.PRACTICE,
        CandidateKind.LIBRARY,
    }
    if any(candidate.kind in content_kinds for candidate in candidates):
        return
''',
    "library fallback with readiness candidates",
)

replace_once(
    "apps/planner/candidate_builders.py",
    '''    policy = plan_policy_for_budget(
        time_budget_minutes=time_budget_minutes,
        due_count=len(due_states),
    )
''',
    '''    policy = plan_policy_for_budget(
        time_budget_minutes=time_budget_minutes,
        due_count=len(due_states),
        primary_need_type=user.primary_need_type,
        secondary_need_type=user.secondary_need_type,
    )
''',
    "aim-aware planner policy call",
)

replace_once(
    "apps/planner/candidate_builders.py",
    '''    candidates = []
    question_by_id = {}
    topic_by_id = {}

    due_question_ids = _build_review_candidates(
''',
    '''    candidates = []
    question_by_id = {}
    topic_by_id = {}

    _build_readiness_candidates(
        user=user,
        plan_date=plan_date,
        time_budget_minutes=time_budget_minutes,
        candidates=candidates,
    )
    due_question_ids = _build_review_candidates(
''',
    "daily readiness candidate assembly",
)

replace_once(
    "apps/planner/candidate_builders.py",
    '''            "priority_score": BASE_SCORE_BY_KIND[candidate.kind],
        }
''',
    '''            "priority_score": BASE_SCORE_BY_KIND[candidate.kind],
            "action_path": candidate.action_path,
            "is_required": candidate.is_required,
        }
''',
    "readiness recommendation payload fields",
)

replace_once(
    "apps/planner/heuristic.py",
    '''        self.weak_area_blocks = 0
        self.selected_ids = set()
''',
    '''        self.weak_area_blocks = 0
        self.readiness_blocks = 0
        self.selected_ids = set()
''',
    "heuristic readiness state",
)

replace_once(
    "apps/planner/heuristic.py",
    '''    if (
        candidate.kind == CandidateKind.WEAK_AREA
        and state.weak_area_blocks >= policy.max_weak_area_blocks
    ):
        return "daily weak-area limit reached"

    return ""
''',
    '''    if (
        candidate.kind == CandidateKind.WEAK_AREA
        and state.weak_area_blocks >= policy.max_weak_area_blocks
    ):
        return "daily weak-area limit reached"

    if candidate.kind in {
        CandidateKind.EVIDENCE,
        CandidateKind.GUIDE,
        CandidateKind.MOCK,
    } and state.readiness_blocks >= policy.max_readiness_blocks:
        return "daily interview-readiness limit reached"

    return ""
''',
    "heuristic readiness constraint",
)

replace_once(
    "apps/planner/heuristic.py",
    '''    elif candidate.kind == CandidateKind.WEAK_AREA:
        state.weak_area_blocks += 1
        state.practice_minutes += candidate.estimated_minutes

    state.last_context_key = candidate.effective_context_key
''',
    '''    elif candidate.kind == CandidateKind.WEAK_AREA:
        state.weak_area_blocks += 1
        state.practice_minutes += candidate.estimated_minutes
    elif candidate.kind in {
        CandidateKind.EVIDENCE,
        CandidateKind.GUIDE,
        CandidateKind.MOCK,
    }:
        state.readiness_blocks += 1

    state.last_context_key = candidate.effective_context_key
''',
    "heuristic readiness selection state",
)

replace_once(
    "apps/planner/heuristic.py",
    '''    review_candidates = [item for item in ranked if item.candidate.kind == CandidateKind.REVIEW]
    roadmap_candidates = [item for item in ranked if item.candidate.kind == CandidateKind.ROADMAP]
    remaining_candidates = [
        item
        for item in ranked
        if item.candidate.kind not in {CandidateKind.REVIEW, CandidateKind.ROADMAP}
    ]

    _choose_from_pass(
        candidates=review_candidates,
''',
    '''    required_candidates = [
        item for item in ranked if item.candidate.is_required
    ]
    review_candidates = [
        item
        for item in ranked
        if item.candidate.kind == CandidateKind.REVIEW
        and not item.candidate.is_required
    ]
    roadmap_candidates = [
        item
        for item in ranked
        if item.candidate.kind == CandidateKind.ROADMAP
        and not item.candidate.is_required
    ]
    remaining_candidates = [
        item
        for item in ranked
        if not item.candidate.is_required
        and item.candidate.kind not in {
            CandidateKind.REVIEW,
            CandidateKind.ROADMAP,
        }
    ]

    _choose_from_pass(
        candidates=required_candidates,
        state=state,
        policy=policy,
        selected=selected,
        rejected=rejected,
    )
    _choose_from_pass(
        candidates=review_candidates,
''',
    "required candidate heuristic pass",
)

replace_once(
    "apps/planner/optimisation.py",
    '''    selected_vars = [model.new_bool_var(f"candidate_{index}") for index in range(len(ranked))]

    model.add(
''',
    '''    selected_vars = [
        model.new_bool_var(f"candidate_{index}")
        for index in range(len(ranked))
    ]

    for index, item in enumerate(ranked):
        if item.candidate.is_required:
            model.add(selected_vars[index] == 1)

    model.add(
''',
    "required candidate optimiser constraints",
)

replace_once(
    "apps/planner/optimisation.py",
    '''    if weak_indices:
        model.add(
            sum(selected_vars[index] for index in weak_indices) <= policy.max_weak_area_blocks
        )

    context_indices = _group_indices(
''',
    '''    if weak_indices:
        model.add(
            sum(selected_vars[index] for index in weak_indices)
            <= policy.max_weak_area_blocks
        )

    readiness_indices = [
        index
        for index, item in enumerate(ranked)
        if item.candidate.kind
        in {
            CandidateKind.EVIDENCE,
            CandidateKind.GUIDE,
            CandidateKind.MOCK,
        }
    ]
    if readiness_indices:
        model.add(
            sum(selected_vars[index] for index in readiness_indices)
            <= policy.max_readiness_blocks
        )

    context_indices = _group_indices(
''',
    "readiness optimiser constraint",
)

replace_once(
    "templates/planner/today.html",
    '''                            <span class="planner-kind planner-kind-{{ recommendation.kind|lower }}">{{ recommendation.get_kind_display }}</span>
                            <span>{{ recommendation.estimated_minutes }} min</span>
''',
    '''                            <span class="planner-kind planner-kind-{{ recommendation.kind|lower }}">{{ recommendation.get_kind_display }}</span>
                            {% if recommendation.is_required %}
                                <span class="planner-required-badge">Required today</span>
                            {% endif %}
                            <span>{{ recommendation.estimated_minutes }} min</span>
''',
    "required planner task badge",
)

replace_once(
    "templates/planner/today.html",
    '''                Rebuilding uses deterministic priorities and scales the number of roadmap, weak-area and practice tasks to the time you enter. Due reviews still come first.
''',
    '''                Rebuilding keeps daily STAR work, due reviews and your selected aims in view, then scales roadmap, readiness and practice blocks to the time you enter.
''',
    "planner settings explanation",
)

replace_once(
    "templates/planner/today.html",
    '''            <ol>
                <li>Time-sensitive due reviews</li>
                <li>The next unfinished roadmap topic</li>
                <li>Recent Again or Hard reviews</li>
                <li>A fresh practice question</li>
            </ol>
''',
    '''            <ol>
                <li>Time-sensitive due reviews</li>
                <li>Daily STAR-story preparation</li>
                <li>Tasks aligned with your primary and secondary aims</li>
                <li>The next unfinished focused-roadmap topic</li>
                <li>Weak areas, evidence, guides and mock practice</li>
            </ol>
''',
    "planner priority explanation",
)

append_once(
    "static/css/planner.css",
    ".planner-required-badge",
    '''.planner-required-badge {
    padding: 0.2rem 0.45rem;
    border: 1px solid currentColor;
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
''',
    "required planner task style",
)

# Update legacy service tests whose one-task assumptions changed because STAR
# practice is now present on every generated plan.
services_path = ROOT / "apps/planner/tests/test_services.py"
services_text = services_path.read_text()
services_text = services_text.replace(
    "def test_short_budget_with_due_reviews_stays_review_only(user):",
    "def test_short_budget_includes_reviews_and_daily_star(user):",
)
services_text = services_text.replace(
    '''    assert kinds == {StudyRecommendation.Kind.REVIEW}
''',
    '''    assert kinds == {
        StudyRecommendation.Kind.REVIEW,
        StudyRecommendation.Kind.STAR,
    }
''',
    1,
)
services_text = services_text.replace(
    '''    recommendation = plan.recommendations.get()
    assert recommendation.kind == StudyRecommendation.Kind.LIBRARY
''',
    '''    recommendation = plan.recommendations.get(
        kind=StudyRecommendation.Kind.LIBRARY
    )
    assert recommendation.kind == StudyRecommendation.Kind.LIBRARY
''',
    1,
)
services_text = services_text.replace(
    '''    recommendation = plan.recommendations.get()

    updated = toggle_recommendation_completion(
        recommendation=recommendation,
    )
    plan.refresh_from_db()

    assert updated.completed_at is not None
    assert plan.status == StudyPlan.Status.COMPLETED

    toggle_recommendation_completion(recommendation=updated)
''',
    '''    recommendations = list(plan.recommendations.all())
    for recommendation in recommendations:
        toggle_recommendation_completion(recommendation=recommendation)
    plan.refresh_from_db()

    assert plan.status == StudyPlan.Status.COMPLETED

    updated = toggle_recommendation_completion(
        recommendation=recommendations[0]
    )
''',
    1,
)
services_text = services_text.replace(
    '''    recommendation = plan.recommendations.get()
    toggle_recommendation_completion(recommendation=recommendation)
''',
    '''    recommendation = plan.recommendations.first()
    toggle_recommendation_completion(recommendation=recommendation)
''',
    1,
)
services_path.write_text(services_text)
print("✓ Applied: legacy planner test updates")

create_once(
    "apps/planner/tests/test_need_type_daily_plan.py",
    '''import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.evidence.models import BehaviouralStory, EvidenceItem
from apps.planner.candidate_builders import build_plan_candidates
from apps.planner.candidates import CandidateKind
from apps.planner.models import StudyRecommendation
from apps.planner.policies import plan_policy_for_budget
from apps.planner.services import generate_daily_plan
from apps.questions.models import Question, TechnicalQuestion

pytestmark = pytest.mark.django_db


def test_daily_plan_contains_required_star_task(user):
    plan = generate_daily_plan(user=user, time_budget_minutes=60)

    star = plan.recommendations.get(kind=StudyRecommendation.Kind.STAR)

    assert star.is_required is True
    assert star.action_path == reverse("evidence:create")


def test_short_plan_keeps_star_and_due_review(user):
    TechnicalQuestion.objects.create(
        owner=user,
        title="Explain queues",
        prompt="Explain queue behaviour.",
        status=Question.Status.READY_FOR_REVIEW,
        topic="Queues",
        intuition="FIFO",
    )

    plan = generate_daily_plan(user=user, time_budget_minutes=20)
    kinds = set(plan.recommendations.values_list("kind", flat=True))

    assert StudyRecommendation.Kind.STAR in kinds
    assert StudyRecommendation.Kind.REVIEW in kinds


def test_incomplete_story_becomes_daily_star_task(user):
    evidence = EvidenceItem.objects.create(
        owner=user,
        source_type=EvidenceItem.SourceType.PROJECT,
        title="ScoreRent",
        summary="Rental decision-support project.",
    )
    story = BehaviouralStory.objects.create(
        evidence=evidence,
        title="Resolving a scoring bug",
        situation="A scoring rule produced a surprising result.",
        actions="I traced and corrected the rule.",
    )

    plan = generate_daily_plan(user=user, time_budget_minutes=60)
    star = plan.recommendations.get(kind=StudyRecommendation.Kind.STAR)

    assert "Strengthen STAR story" in star.title
    assert star.action_path == reverse(
        "evidence:behavioural_story_edit",
        args=[story.pk],
    )


def test_interview_aim_builds_readiness_candidates(user):
    user.primary_need_type = User.NeedType.INTERVIEW_SKILLS
    user.save(update_fields=["primary_need_type"])
    now = timezone.now()

    build = build_plan_candidates(
        user=user,
        time_budget_minutes=120,
        plan_date=timezone.localdate(now),
        now=now,
    )
    kinds = {candidate.kind for candidate in build.candidates}

    assert {
        CandidateKind.STAR,
        CandidateKind.EVIDENCE,
        CandidateKind.GUIDE,
        CandidateKind.MOCK,
    }.issubset(kinds)
    assert build.policy.max_readiness_blocks == 2


def test_primary_aim_changes_daily_capacity_mix():
    learning = plan_policy_for_budget(
        time_budget_minutes=240,
        due_count=0,
        primary_need_type=User.NeedType.LEARN_ORGANISE,
    )
    retention = plan_policy_for_budget(
        time_budget_minutes=240,
        due_count=0,
        primary_need_type=User.NeedType.PRACTISE_RETAIN,
    )

    assert learning.max_roadmaps > retention.max_roadmaps
    assert retention.practice_target_minutes > learning.practice_target_minutes
''',
    "aim-driven daily plan tests",
)

print()
print("Patch 3C applied.")
print("Next:")
print("  python manage.py migrate")
print("  python manage.py check")
print("  python -m pytest apps/planner/tests/test_need_type_daily_plan.py -q")
print("  python -m pytest apps/planner/tests -q")
print("  python -m pytest")
print("  python -m ruff check .")
print("  python -m ruff format --check .")
print("  git diff --check")
