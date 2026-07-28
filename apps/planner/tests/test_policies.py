from apps.planner.policies import plan_policy_for_budget


def test_under_thirty_minutes_is_review_only_when_reviews_are_due():
    policy = plan_policy_for_budget(time_budget_minutes=20, due_count=10)

    assert policy.review_target_minutes == 20
    assert policy.max_roadmaps == 0
    assert policy.practice_target_minutes == 0


def test_one_hour_supports_one_real_learning_block():
    policy = plan_policy_for_budget(time_budget_minutes=60, due_count=0)

    assert policy.max_roadmaps == 1
    assert policy.max_topics_per_roadmap == 1
    assert policy.practice_target_minutes == 15


def test_three_hours_caps_learning_at_two_roadmaps():
    policy = plan_policy_for_budget(time_budget_minutes=180, due_count=0)

    assert policy.max_roadmaps == 2
    assert policy.max_topics_per_roadmap == 1
    assert policy.practice_target_minutes == 45


def test_long_day_never_selects_more_than_four_roadmaps():
    policy = plan_policy_for_budget(time_budget_minutes=720, due_count=0)

    assert policy.max_roadmaps == 4
    assert policy.max_topics_per_roadmap == 2
    assert policy.practice_target_minutes == 120
    assert policy.max_practice_blocks == 3
