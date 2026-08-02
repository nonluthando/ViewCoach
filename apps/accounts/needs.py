from .models import User


NEED_TYPE_EXPERIENCES = {
    User.NeedType.LEARN_ORGANISE: {
        "title": "Learn and organise",
        "description": (
            "Continue focused roadmaps, import trusted learning material, "
            "and keep your notes and resources together."
        ),
        "action_label": "Open learning roadmaps",
        "route_name": "roadmaps:list",
    },
    User.NeedType.PRACTISE_RETAIN: {
        "title": "Practise and retain",
        "description": (
            "Import or create question cards, strengthen weak areas, "
            "and keep knowledge active through review."
        ),
        "action_label": "Import practice material",
        "route_name": "questions:import_start",
    },
    User.NeedType.INTERVIEW_SKILLS: {
        "title": "Build interview skills",
        "description": (
            "Develop STAR stories, organise evidence, use interview guides, "
            "and practise through mock interviews."
        ),
        "action_label": "Open interview hub",
        "route_name": "interview",
    },
}

NEED_KIND_BONUSES = {
    User.NeedType.LEARN_ORGANISE: {"ROADMAP": 15, "LIBRARY": 10},
    User.NeedType.PRACTISE_RETAIN: {
        "REVIEW": 8,
        "WEAK_AREA": 20,
        "PRACTICE": 25,
        "LIBRARY": 10,
    },
    User.NeedType.INTERVIEW_SKILLS: {
        "REVIEW": 5,
        "WEAK_AREA": 10,
        "PRACTICE": 35,
        "LIBRARY": 8,
    },
}


def need_type_experience(value):
    return NEED_TYPE_EXPERIENCES.get(value)


def need_alignment_for_kind(*, primary, secondary, kind):
    points = 0
    labels = []

    primary_bonus = NEED_KIND_BONUSES.get(primary, {}).get(kind, 0)
    if primary_bonus:
        points += primary_bonus
        labels.append(User.NeedType(primary).label)

    secondary_bonus = NEED_KIND_BONUSES.get(secondary, {}).get(kind, 0)
    if secondary_bonus:
        points += max(1, secondary_bonus // 2)
        labels.append(User.NeedType(secondary).label)

    if not points:
        return 0, ""

    if len(labels) == 1:
        explanation = f"This matches your selected aim: {labels[0]}."
    else:
        explanation = (
            "This supports both of your selected aims: "
            f"{labels[0]} and {labels[1]}."
        )
    return points, explanation
