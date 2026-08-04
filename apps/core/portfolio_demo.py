from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.evidence.models import (
    BehaviouralStory,
    DecisionRecord,
    EvidenceItem,
    GoalEvidenceLink,
    ProjectExplanation,
    QuestionEvidenceLink,
    TopicEvidenceLink,
    TopicEvidenceProfile,
)
from apps.goals.models import InterviewGoal, InterviewStage
from apps.interviews.models import MockInterview, MockInterviewItem
from apps.planner.services import generate_daily_plan
from apps.questions.models import (
    BehaviouralQuestion,
    ConceptQuestion,
    DebugQuestion,
    Question,
    TechnicalQuestion,
    UserQuestionNote,
    UserQuestionState,
)
from apps.reviews.models import ReviewAttempt, ReviewState
from apps.roadmaps.models import (
    Roadmap,
    RoadmapSection,
    RoadmapTopic,
    UserRoadmap,
    UserTopicProgress,
    UserTopicResource,
    YouTubePlaylistRoadmap,
    YouTubePlaylistVideo,
    YouTubeRoadmapGroup,
)

DEMO_EMAIL_SUFFIX = "@demo.viewcoach.local"


@dataclass(frozen=True, slots=True)
class PortfolioDemoWorkspace:
    user: User
    custom_roadmap: Roadmap
    youtube_roadmap: Roadmap
    featured_topic: RoadmapTopic
    featured_question: Question
    featured_evidence: EvidenceItem
    goal: InterviewGoal
    mock_interview: MockInterview

    def session_assets(self) -> dict[str, int | str]:
        return {
            "custom_roadmap_slug": self.custom_roadmap.slug,
            "youtube_roadmap_slug": self.youtube_roadmap.slug,
            "featured_topic_id": self.featured_topic.pk,
            "featured_question_id": self.featured_question.pk,
            "featured_evidence_id": self.featured_evidence.pk,
            "goal_id": self.goal.pk,
            "mock_interview_id": self.mock_interview.pk,
        }


def is_portfolio_demo_user(user) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "email", "")
        and user.email.endswith(DEMO_EMAIL_SUFFIX)
    )


def portfolio_demo_users():
    return User.objects.filter(email__endswith=DEMO_EMAIL_SUFFIX)


def cleanup_expired_portfolio_demo_users(*, now=None) -> int:
    current_time = now or timezone.now()
    cutoff = current_time - timedelta(hours=settings.PORTFOLIO_DEMO_TTL_HOURS)
    expired = portfolio_demo_users().filter(date_joined__lt=cutoff)
    count = expired.count()
    expired.delete()
    return count


def delete_portfolio_demo_user(*, user_id: int) -> bool:
    deleted_count, _ = portfolio_demo_users().filter(pk=user_id).delete()
    return deleted_count > 0


def _create_custom_roadmap(*, user: User, token: str):
    roadmap = Roadmap.objects.create(
        title="Backend and AI Interview Sprint",
        slug=f"demo-backend-ai-sprint-{token}",
        description=(
            "A user-created learning path connecting backend fundamentals, "
            "production data design and grounded AI application engineering."
        ),
        kind=Roadmap.Kind.SKILL,
        source=Roadmap.Source.CUSTOM,
        learning_format=Roadmap.LearningFormat.COURSE,
        position=1,
        is_system=False,
        is_published=True,
        created_by=user,
    )
    foundations = RoadmapSection.objects.create(
        roadmap=roadmap,
        title="Backend foundations",
        slug="backend-foundations",
        description="Production API and database reasoning.",
        position=1,
    )
    ai_section = RoadmapSection.objects.create(
        roadmap=roadmap,
        title="AI application engineering",
        slug="ai-application-engineering",
        description="Grounding, evaluation and safe product integration.",
        position=2,
    )
    interview_section = RoadmapSection.objects.create(
        roadmap=roadmap,
        title="Interview explanation",
        slug="interview-explanation",
        description="Turn technical work into clear interview evidence.",
        position=3,
    )

    topic_specs = (
        (
            foundations,
            "REST API design",
            "rest-api-design",
            "Resource modelling, status codes, validation and idempotency.",
            45,
        ),
        (
            foundations,
            "PostgreSQL data modelling",
            "postgresql-data-modelling",
            "Constraints, indexes, transactions and query trade-offs.",
            60,
        ),
        (
            foundations,
            "Testing service boundaries",
            "testing-service-boundaries",
            "Unit, integration and regression tests around meaningful behaviour.",
            45,
        ),
        (
            ai_section,
            "Retrieval-augmented generation",
            "retrieval-augmented-generation",
            "Chunking, retrieval, grounding and answer generation.",
            60,
        ),
        (
            ai_section,
            "AI evaluation and guardrails",
            "ai-evaluation-and-guardrails",
            "Failure modes, quality checks and production controls.",
            45,
        ),
        (
            interview_section,
            "Architecture explanation",
            "architecture-explanation",
            "Explain components, boundaries and data flow without hiding trade-offs.",
            40,
        ),
        (
            interview_section,
            "Decision and trade-off stories",
            "decision-and-trade-off-stories",
            "Describe alternatives, rationale, outcome and what you would change.",
            35,
        ),
    )
    topics = []
    section_positions: dict[int, int] = {}
    for section, title, slug, description, minutes in topic_specs:
        section_positions[section.pk] = section_positions.get(section.pk, 0) + 1
        topics.append(
            RoadmapTopic.objects.create(
                section=section,
                title=title,
                slug=slug,
                description=description,
                estimated_minutes=minutes,
                position=section_positions[section.pk],
            )
        )

    now = timezone.now()
    UserRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        status=UserRoadmap.Status.IN_PROGRESS,
        is_focused=True,
        started_at=now - timedelta(days=12),
    )
    progress_rows = (
        (
            topics[0],
            UserTopicProgress.Status.COMPLETED,
            (
                "Idempotent operations can be retried without changing the intended "
                "result after the first successful request. PUT is normally "
                "idempotent; POST often needs an idempotency key."
            ),
        ),
        (
            topics[1],
            UserTopicProgress.Status.IN_PROGRESS,
            (
                "Use database constraints for invariants, indexes for measured query "
                "patterns and transactions when several writes must succeed together."
            ),
        ),
        (
            topics[2],
            UserTopicProgress.Status.COMPLETED,
            (
                "Test behaviour at the service boundary. Mock unstable external "
                "dependencies, but keep database integration tests for constraints "
                "and transaction behaviour."
            ),
        ),
        (
            topics[3],
            UserTopicProgress.Status.IN_PROGRESS,
            (
                "A RAG response is only as trustworthy as its retrieval and grounding. "
                "Evaluate retrieval separately from final answer quality."
            ),
        ),
        (
            topics[5],
            UserTopicProgress.Status.COMPLETED,
            (
                "Start with the user problem, then data flow, boundaries, important "
                "decisions, failure handling, tests and scaling path."
            ),
        ),
    )
    completed_offsets = {0: 3, 2: 2, 4: 1}
    for index, (topic, status, notes) in enumerate(progress_rows):
        completed_at = (
            now - timedelta(days=completed_offsets.get(index, 1))
            if status == "COMPLETED"
            else None
        )
        UserTopicProgress.objects.create(
            user=user,
            topic=topic,
            status=status,
            notes=notes,
            started_at=now - timedelta(days=11 - index),
            completed_at=completed_at,
        )

    UserTopicResource.objects.create(
        user=user,
        topic=topics[1],
        title="PostgreSQL transaction documentation",
        url="https://www.postgresql.org/docs/current/tutorial-transactions.html",
    )
    UserTopicResource.objects.create(
        user=user,
        topic=topics[3],
        title="ViewCoach RAG architecture notes",
        url="https://github.com/nonluthando/ViewCoach",
    )
    return roadmap, topics


def _create_youtube_roadmap(*, user: User, token: str):
    group = YouTubeRoadmapGroup.objects.create(
        user=user,
        name="Backend interview revision",
        position=1,
    )
    roadmap = Roadmap.objects.create(
        title="System Design Revision Playlist",
        slug=f"demo-system-design-playlist-{token}",
        description=(
            "A sample imported playlist demonstrating source-specific video "
            "tracking without mixing ownership with ViewCoach curriculum."
        ),
        kind=Roadmap.Kind.PRACTICE,
        source=Roadmap.Source.YOUTUBE,
        learning_format=Roadmap.LearningFormat.VIDEO,
        position=2,
        is_system=False,
        is_published=True,
        created_by=user,
    )
    section = RoadmapSection.objects.create(
        roadmap=roadmap,
        title="Playlist videos",
        slug="playlist-videos",
        position=1,
    )
    source = YouTubePlaylistRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        group=group,
        is_favourite=True,
        playlist_id=f"demo-{token}",
        source_url="https://www.youtube.com/",
        channel_title="Demo engineering channel",
        video_count=4,
        available_video_count=4,
        unavailable_video_count=0,
        total_duration_seconds=3280,
    )
    videos = (
        ("Load balancing fundamentals", "load-balancing", 720),
        ("Caching and invalidation", "caching-and-invalidation", 860),
        ("Database replication", "database-replication", 910),
        ("Queues and background work", "queues-and-background-work", 790),
    )
    topics = []
    for position, (title, slug, duration) in enumerate(videos, start=1):
        topic = RoadmapTopic.objects.create(
            section=section,
            title=title,
            slug=slug,
            description="Imported video lesson with ViewCoach notes and progress.",
            external_url="https://www.youtube.com/",
            estimated_minutes=max(5, round(duration / 60)),
            position=position,
        )
        topics.append(topic)
        YouTubePlaylistVideo.objects.create(
            playlist=source,
            topic=topic,
            playlist_item_id=f"demo-item-{token}-{position}",
            video_id=f"demo-video-{position}",
            title=title,
            channel_title="Demo engineering channel",
            duration_seconds=duration,
            position=position,
            available=True,
            embeddable=True,
            made_for_kids=False,
            in_playlist=True,
        )
    now = timezone.now()
    UserRoadmap.objects.create(
        user=user,
        roadmap=roadmap,
        status=UserRoadmap.Status.IN_PROGRESS,
        is_focused=False,
        started_at=now - timedelta(days=8),
    )
    UserTopicProgress.objects.create(
        user=user,
        topic=topics[0],
        status=UserTopicProgress.Status.COMPLETED,
        notes="Compare layer 4 and layer 7 balancing and explain health checks.",
        started_at=now - timedelta(days=8),
        completed_at=now - timedelta(days=7),
    )
    UserTopicProgress.objects.create(
        user=user,
        topic=topics[1],
        status=UserTopicProgress.Status.IN_PROGRESS,
        notes="Always discuss invalidation, consistency and cache ownership.",
        started_at=now - timedelta(days=3),
    )
    return roadmap


def _create_questions(*, user: User, source_topic: RoadmapTopic):
    ready = Question.Status.READY_FOR_REVIEW
    technical = TechnicalQuestion.objects.create(
        owner=user,
        source_topic=source_topic,
        title="Two Sum: explain the trade-off",
        prompt=(
            "Given an array of integers and a target, return the indices of two "
            "numbers that add to the target."
        ),
        difficulty=Question.Difficulty.EASY,
        status=ready,
        topic="Arrays and hashing",
        first_hint="What information from earlier values would remove the inner loop?",
        pattern="Hash map lookup",
        data_structure="Dictionary / hash map",
        intuition=(
            "For every value, compute the complement and check whether it has "
            "already been seen."
        ),
        brute_force="Compare every pair using two nested loops.",
        brute_force_time_complexity="O(n²)",
        brute_force_space_complexity="O(1)",
        optimal_approach=(
            "Store each value and index in a hash map. Return when the complement "
            "already exists."
        ),
        optimal_time_complexity="O(n)",
        optimal_space_complexity="O(n)",
        mistakes=(
            "Adding the current value before checking can allow the same element "
            "to be used twice."
        ),
        progressive_hints=[
            "Think about the complement target - value.",
            "Store information from values you already visited.",
        ],
        code=(
            "def two_sum(numbers, target):\n"
            "    seen = {}\n"
            "    for index, value in enumerate(numbers):\n"
            "        complement = target - value\n"
            "        if complement in seen:\n"
            "            return [seen[complement], index]\n"
            "        seen[value] = index\n"
        ),
    )
    concept = ConceptQuestion.objects.create(
        owner=user,
        source_topic=source_topic,
        title="Explain API idempotency",
        prompt=(
            "What does idempotency mean in an HTTP API, and why does it matter "
            "when clients retry requests?"
        ),
        difficulty=Question.Difficulty.MEDIUM,
        status=ready,
        category=ConceptQuestion.Category.BACKEND,
        canonical_answer=(
            "An idempotent operation can be repeated with the same intended effect "
            "as performing it once. It prevents retries from creating duplicate "
            "business actions."
        ),
        key_points=[
            "GET, PUT and DELETE are designed to be idempotent.",
            "POST can be made retry-safe with an idempotency key.",
            "The server must persist or derive the original outcome.",
        ],
        example=(
            "A payment endpoint stores an idempotency key and returns the original "
            "result instead of charging the customer twice."
        ),
        common_misconception=(
            "Idempotent does not mean every response body must be identical."
        ),
    )
    behavioural = BehaviouralQuestion.objects.create(
        owner=user,
        title="Describe a difficult technical decision",
        prompt=(
            "Tell me about a technical decision where several reasonable options "
            "had meaningful trade-offs."
        ),
        difficulty=Question.Difficulty.MEDIUM,
        status=ready,
        star_answer=(
            "I kept curated, imported and user-created roadmaps separate by source "
            "and ownership while reusing one shared progress engine. This required "
            "source-aware routing, but avoided duplicated learning logic and made "
            "planner behaviour consistent."
        ),
        leadership_principles="Ownership, judgement, simplification",
        stories="ViewCoach roadmap architecture",
        follow_ups=(
            "What alternatives did you reject?\n"
            "What new complexity did the decision introduce?"
        ),
        competencies=["Architecture", "Trade-off reasoning", "Ownership"],
        star_outline={
            "situation": "Several learning sources needed progress and planning.",
            "task": "Preserve ownership without duplicating the learning backend.",
            "action": "Use shared roadmap domain objects with source metadata.",
            "result": "Every source participates in one progress and planner engine.",
        },
        follow_up_questions=[
            "How are permissions enforced?",
            "What would you change at larger scale?",
        ],
        common_mistakes=[
            "Explaining only the final design without the rejected alternatives."
        ],
    )
    debug = DebugQuestion.objects.create(
        owner=user,
        title="Fix a transaction locking failure",
        prompt=(
            "A PostgreSQL test fails with 'FOR UPDATE cannot be applied to the "
            "nullable side of an outer join'. Diagnose and fix it."
        ),
        difficulty=Question.Difficulty.HARD,
        status=ready,
        repository="Django service using select_for_update and a nullable relation.",
        bug_type=DebugQuestion.BugType.OTHER,
        failing_test_or_symptom=(
            "The service raises django.db.utils.NotSupportedError on PostgreSQL."
        ),
        broken_code=(
            "Roadmap.objects.select_for_update().get(\n"
            "    pk=roadmap.pk,\n"
            "    external_course__isnull=True,\n"
            ")"
        ),
        likely_bug=(
            "The nullable relation introduces an outer join, and PostgreSQL refuses "
            "to lock the nullable side."
        ),
        reasoning=(
            "Lock the concrete Roadmap row first. Check the optional relation in a "
            "separate query."
        ),
        fix=(
            "Remove the nullable relation filter from the locking query, then use "
            "ExternalCourseRoadmap.objects.filter(roadmap=locked).exists()."
        ),
        tests=(
            "Run the service and view suites on PostgreSQL and preserve the "
            "ownership assertions."
        ),
        common_mistake="Assuming SQLite reproduces PostgreSQL row-lock semantics.",
    )

    questions = [technical, concept, behavioural, debug]
    now = timezone.now()
    due_offsets = (-2, 3, -1, 6)
    for index, question in enumerate(questions):
        UserQuestionState.objects.create(
            user=user,
            question=question,
            status=UserQuestionState.Status.READY_FOR_REVIEW,
            bookmarked=index in {1, 2},
            started_at=now - timedelta(days=10 - index),
            ready_at=now - timedelta(days=8 - index),
        )
        UserQuestionNote.objects.create(
            user=user,
            question=question,
            notes="Demo notes showing how a candidate refines an interview answer.",
            mistakes=(
                "Lead with the core idea before details; name the trade-off explicitly."
            ),
            code_notes=(
                "Trace the example manually before discussing complexity."
                if question.question_type == Question.Type.TECHNICAL
                else ""
            ),
            behavioural_notes=(
                "Keep the action section focused on personal contribution."
                if question.question_type == Question.Type.BEHAVIOURAL
                else ""
            ),
        )
        ReviewState.objects.create(
            user=user,
            question=question,
            due_at=now + timedelta(days=due_offsets[index]),
            interval_days=max(1, index + 1),
            ease_factor=Decimal("2.50"),
            repetitions=index,
            lapses=1 if index == 3 else 0,
            last_reviewed_at=now - timedelta(days=5 - index),
        )

    concept_state = ReviewState.objects.get(user=user, question=concept)
    previous_due = now - timedelta(days=5)
    ReviewAttempt.objects.create(
        state=concept_state,
        rating=ReviewAttempt.Rating.GOOD,
        reviewed_at=now - timedelta(days=4),
        previous_due_at=previous_due,
        scheduled_due_at=now + timedelta(days=3),
        previous_interval_days=1,
        scheduled_interval_days=7,
        previous_ease_factor=Decimal("2.50"),
        scheduled_ease_factor=Decimal("2.50"),
    )
    return questions


def _create_evidence(*, user: User):
    viewcoach = EvidenceItem.objects.create(
        owner=user,
        source_type=EvidenceItem.SourceType.PROJECT,
        title="ViewCoach",
        role_or_context="Product designer and full-stack developer",
        summary=(
            "An adaptive interview-preparation platform connecting learning, "
            "retrieval practice, evidence and explainable daily planning."
        ),
        problem=(
            "Interview preparation is fragmented across notes, courses, question "
            "lists and calendars, leaving candidates unsure what matters next."
        ),
        personal_contribution=(
            "Designed the product architecture and implemented Django domains, "
            "PostgreSQL data design, roadmap workflows, planning logic, AI "
            "boundaries, tests and the interface."
        ),
        technologies=(
            "Python, Django, PostgreSQL, pgvector, OR-Tools, Gemini, HTML, CSS"
        ),
        outcomes=(
            "Built an end-to-end system where goals, learning progress, reviews "
            "and evidence influence one explainable plan."
        ),
        lessons=(
            "Keep ownership explicit, make AI output reviewable and prefer shared "
            "domain behaviour over duplicated feature-specific backends."
        ),
        evidence_url="https://github.com/nonluthando/ViewCoach",
    )
    scorerent = EvidenceItem.objects.create(
        owner=user,
        source_type=EvidenceItem.SourceType.PROJECT,
        title="ScoreRent",
        role_or_context="Backend and product developer",
        summary=(
            "A FastAPI and PostgreSQL rental decision-support tool that turns "
            "affordability and application conditions into an explainable score."
        ),
        problem=(
            "Rental applicants often cannot tell whether a listing is realistically "
            "affordable or which application weaknesses they can address."
        ),
        personal_contribution=(
            "Designed the scoring rules, authentication flow, persistence and "
            "explainable results experience."
        ),
        technologies="Python, FastAPI, PostgreSQL, Jinja2, Render",
        outcomes=(
            "Produced a score, confidence level, reasons and practical next actions."
        ),
        lessons=(
            "Decision-support outputs need transparent rules and bounded claims."
        ),
        evidence_url="https://scorerent.onrender.com",
    )
    work = EvidenceItem.objects.create(
        owner=user,
        source_type=EvidenceItem.SourceType.WORK,
        title="Production AI application support",
        organisation="Foondamate",
        role_or_context="Junior software and AI application work",
        summary=(
            "Supported production features involving document replies, curriculum "
            "retrieval, automated tests and application integrations."
        ),
        personal_contribution=(
            "Implemented and tested backend behaviour across Python and PHP services."
        ),
        technologies="Python, Flask, PHP, Laravel, pytest, ChromaDB",
        outcomes=(
            "Improved regression coverage and delivered production-facing feature work."
        ),
        lessons=(
            "Small production changes require careful dependency, version and "
            "failure-path reasoning."
        ),
    )

    ProjectExplanation.objects.create(
        evidence=viewcoach,
        quick_pitch=(
            "ViewCoach tells a candidate what to study next and why while keeping "
            "their learning, practice and interview evidence connected."
        ),
        two_minute_answer=(
            "The platform is organised into Django domains for accounts, goals, "
            "roadmaps, questions, reviews, evidence, interviews and planning. "
            "Services connect those domains without placing business rules in "
            "templates. The planner builds candidate tasks, scores them against "
            "urgency and user aims, then selects work that fits the available time."
        ),
        architecture=(
            "Modular Django apps, PostgreSQL persistence, pgvector retrieval, "
            "service-layer orchestration and OR-Tools plan optimisation."
        ),
        key_decisions=(
            "Use one roadmap backend across sources; retain source ownership; "
            "require approval before generated cards enter review."
        ),
        difficult_bug=(
            "A PostgreSQL row-lock query failed because a nullable relation created "
            "an outer join. The fix separated the concrete row lock from the "
            "optional-relation check."
        ),
        testing_and_verification=(
            "Model, service, view, migration and planner-policy tests run through pytest."
        ),
        ai_use=(
            "AI supports grounded help and editable draft generation; it does not "
            "silently become the source of truth."
        ),
        tradeoffs=(
            "A richer connected model increases implementation complexity, but "
            "produces more explainable recommendations and less duplicated logic."
        ),
        improvements=(
            "Add stronger retrieval evaluation, queue expensive generation work "
            "and add demo analytics that preserve visitor privacy."
        ),
        scaling=(
            "Use background jobs, cache stable retrieval results and isolate "
            "high-volume demo data from long-lived user records."
        ),
        likely_follow_ups=(
            "Why Django?\nHow is planner scoring explained?\n"
            "What happens when the optimiser is unavailable?"
        ),
    )
    ProjectExplanation.objects.create(
        evidence=scorerent,
        quick_pitch=(
            "ScoreRent helps a renter judge whether a listing is a realistic match "
            "and explains the result instead of returning a black-box score."
        ),
        two_minute_answer=(
            "FastAPI handles the application workflow, PostgreSQL stores profiles "
            "and evaluations, and explicit rules produce the score, verdict, "
            "confidence, reasons and next actions."
        ),
        architecture="FastAPI services, PostgreSQL persistence and server-rendered views.",
        key_decisions=(
            "Use explicit scoring rules before adding a predictive model so every "
            "penalty and recommendation remains auditable."
        ),
        testing_and_verification="Boundary tests cover score bands and rule interactions.",
        tradeoffs=(
            "Rules are easier to audit but require deliberate maintenance as the "
            "product learns from real outcomes."
        ),
        improvements="Add calibrated data-driven components after collecting outcomes.",
        scaling="Separate evaluation jobs and cache listing metadata.",
    )
    DecisionRecord.objects.create(
        evidence=viewcoach,
        title="Use one roadmap backend for every learning source",
        context=(
            "Curated roadmaps, YouTube imports and personal roadmaps all need "
            "progress, notes and planner integration."
        ),
        alternatives=(
            "Build separate progress systems for each source; or flatten every "
            "source into one catalogue with no ownership distinction."
        ),
        decision=(
            "Keep source-specific ownership and import metadata while sharing the "
            "Roadmap, Section, Topic and Progress domain."
        ),
        rationale=(
            "This reuses stable learning behaviour without pretending every source "
            "has the same owner or update lifecycle."
        ),
        tradeoffs=(
            "Routing and permissions become more explicit, but duplicated progress "
            "logic and inconsistent planner behaviour are avoided."
        ),
        outcome="New roadmap sources can participate in the same planning engine.",
        would_choose_again=DecisionRecord.RepeatChoice.YES,
        reflection=(
            "I would establish the source boundaries earlier and document them as "
            "part of the domain model."
        ),
    )
    BehaviouralStory.objects.create(
        evidence=viewcoach,
        title="Recovering a deployment-blocking migration",
        situation=(
            "A PostgreSQL migration failed during deployment because schema and "
            "index operations were grouped inside one transaction."
        ),
        task="Restore deployment safely without losing existing roadmap data.",
        actions=(
            "Traced the error to pending trigger events, made the migration "
            "non-atomic and kept the data-preservation operation explicitly atomic."
        ),
        result=(
            "The deployment could rerun safely and current user learning choices "
            "were preserved."
        ),
        reflection=(
            "Database-specific behaviour must be tested as part of deployment "
            "design, not treated as an environment detail."
        ),
        competencies="Debugging, ownership, database reasoning, risk management",
        follow_up_questions=(
            "Why was the migration originally atomic?\n"
            "How did you verify existing data would survive?\n"
            "What would you automate next?"
        ),
    )
    return viewcoach, scorerent, work


def _create_goal_and_links(
    *,
    user: User,
    roadmaps: list[Roadmap],
    evidence: list[EvidenceItem],
):
    goal = InterviewGoal.objects.create(
        user=user,
        title="Junior Software and AI Engineering Interviews",
        goal_type=InterviewGoal.GoalType.GENERAL_PREPARATION,
        role_title="Junior Software / AI Engineer",
        weekly_minutes=600,
        status=InterviewGoal.Status.ACTIVE,
        is_primary=True,
    )
    goal.roadmaps.add(*roadmaps)
    InterviewStage.objects.create(
        goal=goal,
        stage_type=InterviewStage.StageType.OA,
        position=1,
        completed_at=timezone.now() - timedelta(days=5),
    )
    InterviewStage.objects.create(
        goal=goal,
        stage_type=InterviewStage.StageType.TECHNICAL,
        is_current=True,
        scheduled_for=timezone.localdate() + timedelta(days=9),
        position=2,
    )
    InterviewStage.objects.create(
        goal=goal,
        stage_type=InterviewStage.StageType.BEHAVIOURAL,
        scheduled_for=timezone.localdate() + timedelta(days=14),
        position=3,
    )
    GoalEvidenceLink.objects.create(
        user=user,
        goal=goal,
        evidence=evidence[0],
        relevance=GoalEvidenceLink.Relevance.CORE,
        framing_notes=(
            "Use ViewCoach to explain architecture, planning and engineering trade-offs."
        ),
    )
    GoalEvidenceLink.objects.create(
        user=user,
        goal=goal,
        evidence=evidence[1],
        relevance=GoalEvidenceLink.Relevance.SUPPORTING,
        framing_notes=(
            "Use ScoreRent to explain rules, API design and transparent decision support."
        ),
    )
    return goal


def _link_evidence(
    *,
    user: User,
    topic: RoadmapTopic,
    question: Question,
    evidence: EvidenceItem,
):
    profile = TopicEvidenceProfile.objects.create(
        user=user,
        topic=topic,
        readiness=TopicEvidenceProfile.Readiness.INTERVIEW_READY,
        personal_angle=(
            "I implemented this boundary in ViewCoach and diagnosed a PostgreSQL "
            "locking failure around it."
        ),
        interview_angle=(
            "Explain why database semantics must be tested on the production engine."
        ),
        evidence_gap="Add a small performance benchmark for concurrent writes.",
        follow_up_questions=(
            "Why not rely on application validation alone?\n"
            "How would this behave under concurrent requests?"
        ),
    )
    TopicEvidenceLink.objects.create(
        profile=profile,
        evidence=evidence,
        connection_note="The project contains the concrete implementation and fix.",
    )
    QuestionEvidenceLink.objects.create(
        user=user,
        question=question,
        evidence=evidence,
        answer_angle=(
            "Use the roadmap-domain decision to show alternatives, rationale and outcome."
        ),
    )


def _create_mock_interview(
    *,
    user: User,
    goal: InterviewGoal,
    questions: list[Question],
):
    started = timezone.now() - timedelta(days=2, minutes=35)
    completed = started + timedelta(minutes=31)
    interview = MockInterview.objects.create(
        user=user,
        goal=goal,
        focus=MockInterview.Focus.MIXED,
        duration_minutes=30,
        question_count=3,
        status=MockInterview.Status.COMPLETED,
        started_at=started,
        completed_at=completed,
    )
    assessments = (
        MockInterviewItem.Assessment.CONFIDENT,
        MockInterviewItem.Assessment.PARTIAL,
        MockInterviewItem.Assessment.CONFIDENT,
    )
    response_notes = (
        "Explained the hash-map approach and both complexity trade-offs clearly.",
        "Good definition; add a sharper payment-retry example earlier.",
        "Strong ownership story. Keep the result section more measurable.",
    )
    for position, question in enumerate(questions[:3], start=1):
        specific = question.specific
        answer = getattr(
            specific,
            "canonical_answer",
            getattr(specific, "star_answer", getattr(specific, "optimal_approach", "")),
        )
        MockInterviewItem.objects.create(
            interview=interview,
            question=question,
            position=position,
            question_title=question.title,
            prompt_snapshot=question.prompt,
            answer_snapshot=answer,
            guidance_snapshot=(
                "Lead with the core idea, give one concrete example and name the trade-off."
            ),
            question_type=question.question_type,
            difficulty=question.difficulty,
            response_notes=response_notes[position - 1],
            assessment=assessments[position - 1],
            answered_at=started + timedelta(minutes=position * 9),
        )
    return interview


@transaction.atomic
def create_portfolio_demo_workspace() -> PortfolioDemoWorkspace:
    token = uuid4().hex[:12]
    user = User.objects.create_user(
        email=f"recruiter-{token}{DEMO_EMAIL_SUFFIX}",
        password=None,
        first_name="Demo",
        last_name="User",
        primary_need_type=User.NeedType.INTERVIEW_SKILLS,
        secondary_need_type=User.NeedType.PRACTISE_RETAIN,
    )
    custom_roadmap, custom_topics = _create_custom_roadmap(user=user, token=token)
    youtube_roadmap = _create_youtube_roadmap(user=user, token=token)
    questions = _create_questions(user=user, source_topic=custom_topics[0])
    evidence = list(_create_evidence(user=user))
    goal = _create_goal_and_links(
        user=user,
        roadmaps=[custom_roadmap, youtube_roadmap],
        evidence=evidence,
    )
    _link_evidence(
        user=user,
        topic=custom_topics[1],
        question=questions[2],
        evidence=evidence[0],
    )
    mock_interview = _create_mock_interview(
        user=user,
        goal=goal,
        questions=questions,
    )
    demo_plan = generate_daily_plan(user=user, time_budget_minutes=165, force=True)
    first_recommendation = demo_plan.recommendations.order_by("position", "pk").first()
    if first_recommendation is not None:
        first_recommendation.completed_at = timezone.now()
        first_recommendation.save(update_fields=["completed_at"])

    return PortfolioDemoWorkspace(
        user=user,
        custom_roadmap=custom_roadmap,
        youtube_roadmap=youtube_roadmap,
        featured_topic=custom_topics[1],
        featured_question=questions[1],
        featured_evidence=evidence[0],
        goal=goal,
        mock_interview=mock_interview,
    )
