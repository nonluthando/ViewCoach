from dataclasses import dataclass

REVIEW_MINUTES_PER_QUESTION = 3
ROADMAP_BLOCK_MINUTES = 45
ROADMAP_BLOCK_MAX_MINUTES = 90
MAX_ROADMAPS_PER_DAY = 4
MAX_TOPICS_PER_ROADMAP = 2
MAX_REVIEW_GROUPS = 3
PRACTICE_BLOCK_MINUTES = 15
PRACTICE_BLOCK_MAX_MINUTES = 45
WEAK_AREA_BLOCK_MINUTES = 15


@dataclass(frozen=True)
class DailyPlanPolicy:
    time_budget_minutes: int
    review_target_minutes: int
    max_roadmaps: int
    max_topics_per_roadmap: int
    practice_target_minutes: int
    max_practice_blocks: int
    max_weak_area_blocks: int


def _round_down_to_five(minutes):
    return max(0, (minutes // 5) * 5)


def _roadmap_limit_for_budget(time_budget_minutes):
    if time_budget_minutes < 60:
        return 0
    if time_budget_minutes < 120:
        return 1
    if time_budget_minutes < 240:
        return 2
    if time_budget_minutes < 360:
        return 3
    return MAX_ROADMAPS_PER_DAY


def _desired_practice_minutes(time_budget_minutes):
    if time_budget_minutes < 30:
        return 0
    if time_budget_minutes < 120:
        return 20
    if time_budget_minutes < 240:
        return max(20, _round_down_to_five(time_budget_minutes * 25 // 100))
    if time_budget_minutes < 360:
        return max(30, _round_down_to_five(time_budget_minutes * 25 // 100))
    return min(120, max(45, _round_down_to_five(time_budget_minutes * 30 // 100)))


def _review_target_minutes(*, time_budget_minutes, due_count):
    if due_count <= 0:
        return 0

    review_demand = due_count * REVIEW_MINUTES_PER_QUESTION
    if time_budget_minutes < 30:
        return min(time_budget_minutes, review_demand)

    review_share = _round_down_to_five(time_budget_minutes * 25 // 100)
    review_ceiling = min(60, max(20, review_share))
    return min(time_budget_minutes, review_demand, review_ceiling)


def plan_policy_for_budget(*, time_budget_minutes, due_count):
    budget = max(1, int(time_budget_minutes))
    review_target = _review_target_minutes(
        time_budget_minutes=budget,
        due_count=max(0, due_count),
    )
    minutes_after_review = max(0, budget - review_target)

    band_roadmap_limit = _roadmap_limit_for_budget(budget)
    roadmap_limit_that_fits = min(
        band_roadmap_limit,
        minutes_after_review // ROADMAP_BLOCK_MINUTES,
    )
    minimum_learning_minutes = roadmap_limit_that_fits * ROADMAP_BLOCK_MINUTES

    desired_practice = _desired_practice_minutes(budget)
    practice_room = max(0, minutes_after_review - minimum_learning_minutes)
    practice_target = min(desired_practice, practice_room)

    if budget < 120:
        max_practice_blocks = 1
    elif budget < 360:
        max_practice_blocks = 2
    else:
        max_practice_blocks = 3

    return DailyPlanPolicy(
        time_budget_minutes=budget,
        review_target_minutes=review_target,
        max_roadmaps=roadmap_limit_that_fits,
        max_topics_per_roadmap=(MAX_TOPICS_PER_ROADMAP if budget >= 240 else 1),
        practice_target_minutes=practice_target,
        max_practice_blocks=max_practice_blocks,
        max_weak_area_blocks=2 if budget >= 240 else 1,
    )
