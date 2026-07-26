from dataclasses import dataclass


@dataclass(frozen=True)
class TimedWorkflowStep:
    minutes: str
    title: str
    actions: tuple[str, ...]


@dataclass(frozen=True)
class PromptTemplate:
    key: str
    title: str
    use_when: str
    prompt: str
    why_it_works: str
    weak_prompt: str


@dataclass(frozen=True)
class CommonMistake:
    mistake: str
    why_it_hurts: str
    better_action: str


TIMED_REPOSITORY_WORKFLOW = (
    TimedWorkflowStep(
        minutes="0–5",
        title="Orient yourself",
        actions=(
            "Read the task once without changing code.",
            "Identify the requested fix, feature and expected deliverables.",
            "Inspect the repository structure, README and test commands.",
            "Write down constraints such as language, dependencies and time.",
        ),
    ),
    TimedWorkflowStep(
        minutes="5–12",
        title="Run and classify the failures",
        actions=(
            "Run the full test suite before making changes.",
            "Read every failing test name, assertion and actual value.",
            "Group failures that may share one root cause.",
            "Separate setup problems from genuine application failures.",
        ),
    ),
    TimedWorkflowStep(
        minutes="12–22",
        title="Trace the existing behaviour",
        actions=(
            "Open the failing test and the smallest relevant production path.",
            "Trace where the expected and actual values diverge.",
            "Search for existing helpers, conventions and similar implementations.",
            "Form a root-cause hypothesis before asking AI for a fix.",
        ),
    ),
    TimedWorkflowStep(
        minutes="22–32",
        title="Use AI for focused investigation",
        actions=(
            "Give AI the task, failing assertion, relevant code and constraints.",
            "Ask for an explanation and ranked root-cause hypotheses first.",
            "Challenge unsupported assumptions and request repository evidence.",
            "Reject broad rewrites and keep the proposed change narrow.",
        ),
    ),
    TimedWorkflowStep(
        minutes="32–40",
        title="Implement the smallest justified fix",
        actions=(
            "Change the underlying cause rather than patching the symptom.",
            "Keep the diff easy to explain.",
            "Run the specific failing test immediately.",
            "Revisit the hypothesis if the targeted test still fails.",
        ),
    ),
    TimedWorkflowStep(
        minutes="40–50",
        title="Add the requested feature",
        actions=(
            "Confirm the expected behaviour and edge cases.",
            "Follow existing repository patterns.",
            "Add or update focused tests where appropriate.",
            "Avoid unrelated refactoring while the clock is running.",
        ),
    ),
    TimedWorkflowStep(
        minutes="50–56",
        title="Verify the whole change",
        actions=(
            "Run targeted tests and then the complete suite.",
            "Run formatting, linting or type checks available in the repository.",
            "Review the final diff for unrelated changes and hidden assumptions.",
            "Manually reason through important boundaries and error paths.",
        ),
    ),
    TimedWorkflowStep(
        minutes="56–60",
        title="Prepare the handover",
        actions=(
            "Write a concise AI-use note.",
            "State what was fixed, how it was verified and what remains uncertain.",
            "Prepare to explain the root cause and each important decision.",
            "Stop changing code unless a final check reveals a real issue.",
        ),
    ),
)


PROMPT_TEMPLATES = (
    PromptTemplate(
        key="repository-orientation",
        title="Understand an unfamiliar repository",
        use_when="You need a grounded map before touching the code.",
        prompt=(
            "Do not propose code changes yet. Based only on the files below, explain the "
            "repository structure, the request flow relevant to this task, the test command, "
            "and the three files I should inspect next. List any assumptions separately."
        ),
        why_it_works=(
            "It asks for orientation, limits the evidence and prevents premature rewriting."
        ),
        weak_prompt="Explain this repository.",
    ),
    PromptTemplate(
        key="failing-assertion",
        title="Interpret a failing test",
        use_when="A test fails and you need to understand the expectation.",
        prompt=(
            "Do not fix the code yet. Explain what this test expects, what the actual result "
            "shows, and where the two values likely diverge. Trace the relevant execution path "
            "using the supplied test and implementation. Mark anything not proven by the code."
        ),
        why_it_works=(
            "It separates expected behaviour, observed behaviour and unverified assumptions."
        ),
        weak_prompt="Why is this test failing?",
    ),
    PromptTemplate(
        key="root-cause-hypotheses",
        title="Rank likely root causes",
        use_when="The symptom could come from several places.",
        prompt=(
            "Rank the three most likely root causes for this failure. For each one, cite the "
            "specific line, value or control-flow fact that supports it, explain what evidence "
            "would disprove it, and suggest the smallest diagnostic check to run next."
        ),
        why_it_works=(
            "It forces evidence, falsifiability and a cheap next step instead of guesswork."
        ),
        weak_prompt="Find the bug and fix it.",
    ),
    PromptTemplate(
        key="compare-fixes",
        title="Compare possible fixes",
        use_when="You understand the cause but have more than one valid implementation.",
        prompt=(
            "Compare these two possible fixes against the current repository conventions. "
            "Evaluate correctness, regression risk, readability, scope and testability. "
            "Recommend the smallest safe option and explain what behaviour it preserves."
        ),
        why_it_works=(
            "It makes trade-offs explicit and discourages choosing the most elaborate solution."
        ),
        weak_prompt="Which solution is better?",
    ),
    PromptTemplate(
        key="small-feature",
        title="Plan a small feature",
        use_when="The assessment asks for a contained feature after the bugs are fixed.",
        prompt=(
            "Before writing code, turn this feature request into observable behaviours and edge "
            "cases. Identify the existing files and patterns that should be reused. Propose a "
            "minimal implementation plan and the focused tests that would prove it works."
        ),
        why_it_works=(
            "It converts vague requirements into testable behaviour and keeps the change local."
        ),
        weak_prompt="Add this feature.",
    ),
    PromptTemplate(
        key="edge-cases",
        title="Generate useful edge cases",
        use_when="Visible tests pass but you need confidence beyond the supplied cases.",
        prompt=(
            "Given this requirement and implementation, list the highest-risk missing cases. "
            "Prioritise boundaries, invalid input, empty values, duplicate data, ordering, "
            "authorisation and error paths. For each case, state the expected behaviour."
        ),
        why_it_works=(
            "It directs attention to risk categories rather than producing random test data."
        ),
        weak_prompt="Give me more tests.",
    ),
    PromptTemplate(
        key="diff-review",
        title="Review the final diff",
        use_when="The implementation works and you need a second-pass review.",
        prompt=(
            "Review this diff against the original task. Look only for correctness problems, "
            "missed edge cases, regressions, security issues, unnecessary scope and tests that "
            "could pass for the wrong reason. Do not suggest style-only refactors."
        ),
        why_it_works=(
            "It gives the review a clear standard and prevents low-value stylistic churn."
        ),
        weak_prompt="Review my code.",
    ),
    PromptTemplate(
        key="explain-my-change",
        title="Prepare to explain the solution",
        use_when="You need to defend the work in a review or pair-programming interview.",
        prompt=(
            "Act as an interviewer reviewing this change. Ask me one question at a time about "
            "the root cause, chosen fix, alternatives, edge cases, verification and limitations. "
            "Challenge any answer that is vague or unsupported by the code."
        ),
        why_it_works=(
            "It tests whether you truly understand the change instead of memorising a summary."
        ),
        weak_prompt="Help me explain this code.",
    ),
)


VERIFICATION_CHECKLIST = (
    "The change matches the written requirement, not only the visible test.",
    "I can explain every changed line without referring to the AI conversation.",
    "The targeted failing test passes.",
    "The complete test suite passes.",
    "Relevant linting, formatting and type checks pass.",
    "Important boundaries, invalid inputs and error paths were considered.",
    "Existing behaviour outside the task was preserved.",
    "No unverified API, dependency or repository helper was introduced.",
    "No secrets, private data or unsafe defaults were added.",
    "The final diff contains no unrelated refactoring or generated clutter.",
    "Tests would fail if the implementation were meaningfully wrong.",
    "Remaining limitations or uncertainty are stated honestly.",
)


AI_USE_NOTE_TEMPLATE = (
    "What I used AI for:",
    "What context I provided:",
    "What AI suggested:",
    "What I accepted:",
    "What I changed or rejected:",
    "How I verified the result:",
    "Known limitations or remaining uncertainty:",
)


SPEAK_ALOUD_LINES = (
    "The test expects X, but the function currently returns Y.",
    "I am tracing where that value changes before editing anything.",
    "This suggestion assumes a helper exists, so I will verify that in the repository.",
    "The smallest underlying fix appears to be here because both failures share this path.",
    "I am running the targeted test first so the feedback stays specific.",
    "The focused test passes; now I am checking the full suite for regressions.",
    "I rejected the broader rewrite because it changed behaviour outside the request.",
    "The remaining risk is this edge case, so I am adding one focused test.",
)


COMMON_MISTAKES = (
    CommonMistake(
        mistake="Asking AI to fix the whole repository",
        why_it_hurts="The output becomes broad, speculative and difficult to verify.",
        better_action="Ask for explanation, evidence and one narrow next step.",
    ),
    CommonMistake(
        mistake="Changing code before running the tests",
        why_it_hurts="You lose the baseline and may solve the wrong problem.",
        better_action="Run the full suite and record every failure first.",
    ),
    CommonMistake(
        mistake="Reading only the first failing assertion",
        why_it_hurts="Later assertions may reveal the true shared cause.",
        better_action="Inspect the entire failing test and all reported values.",
    ),
    CommonMistake(
        mistake="Accepting a suggestion because it looks familiar",
        why_it_hurts="Plausible code can use the wrong API or violate repository conventions.",
        better_action="Verify the interface, installed version and existing patterns.",
    ),
    CommonMistake(
        mistake="Rewriting working code during a timed task",
        why_it_hurts="It increases regression risk and consumes verification time.",
        better_action="Prefer the smallest justified change that preserves behaviour.",
    ),
    CommonMistake(
        mistake="Stopping after one targeted test passes",
        why_it_hurts="The fix may break another path or satisfy the test for the wrong reason.",
        better_action="Run the complete suite and inspect the final diff.",
    ),
    CommonMistake(
        mistake="Letting AI add an unnecessary dependency",
        why_it_hurts="It adds supply-chain, compatibility and setup risk.",
        better_action="Use the repository's existing tools unless the dependency is justified.",
    ),
    CommonMistake(
        mistake="Submitting code you cannot explain",
        why_it_hurts="The follow-up interview will expose the gap immediately.",
        better_action="Simplify, rewrite or reject anything you do not understand.",
    ),
    CommonMistake(
        mistake="Writing a vague AI-use note",
        why_it_hurts="It hides your judgement and makes ownership unclear.",
        better_action="Separate what was suggested, accepted, changed, rejected and verified.",
    ),
)
