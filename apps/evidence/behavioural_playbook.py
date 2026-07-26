BEHAVIOURAL_COMPETENCIES = (
    {
        "key": "ownership",
        "label": "Ownership",
        "aliases": ("ownership", "accountability", "responsibility"),
        "questions": (
            "Tell me about a time you took ownership beyond your assigned task.",
            "Describe a problem you noticed and fixed without being asked.",
        ),
    },
    {
        "key": "problem-solving",
        "label": "Problem solving",
        "aliases": ("problem solving", "problem-solving", "debugging", "analysis"),
        "questions": (
            "Tell me about a difficult problem you had to break down.",
            "Describe a time your first approach did not work.",
        ),
    },
    {
        "key": "teamwork",
        "label": "Teamwork",
        "aliases": ("teamwork", "collaboration", "team"),
        "questions": (
            "Tell me about a time you helped a team deliver.",
            "Describe how you worked with someone whose approach differed from yours.",
        ),
    },
    {
        "key": "communication",
        "label": "Communication",
        "aliases": ("communication", "stakeholder", "documentation", "presentation"),
        "questions": (
            "Tell me about a time you explained something complex clearly.",
            "Describe a communication mistake and how you corrected it.",
        ),
    },
    {
        "key": "learning-adaptability",
        "label": "Learning and adaptability",
        "aliases": ("learning", "adaptability", "adaptable", "growth"),
        "questions": (
            "Tell me about a time you had to learn something quickly.",
            "Describe how you handled a major change in requirements or context.",
        ),
    },
    {
        "key": "conflict",
        "label": "Conflict and disagreement",
        "aliases": ("conflict", "disagreement", "negotiation", "challenge"),
        "questions": (
            "Tell me about a disagreement with a teammate.",
            "Describe a time you challenged a decision respectfully.",
        ),
    },
    {
        "key": "failure-recovery",
        "label": "Failure and recovery",
        "aliases": ("failure", "recovery", "mistake", "resilience"),
        "questions": (
            "Tell me about a meaningful mistake or failure.",
            "Describe a setback and what you changed afterwards.",
        ),
    },
    {
        "key": "leadership-initiative",
        "label": "Leadership and initiative",
        "aliases": ("leadership", "initiative", "mentoring", "influence"),
        "questions": (
            "Tell me about a time you led without formal authority.",
            "Describe a time you helped someone else succeed.",
        ),
    },
)

BEHAVIOURAL_COMPETENCY_BY_KEY = {
    competency["key"]: competency for competency in BEHAVIOURAL_COMPETENCIES
}


def story_matches_competency(story, competency):
    competency_text = story.competencies.lower()
    return any(alias in competency_text for alias in competency["aliases"])
