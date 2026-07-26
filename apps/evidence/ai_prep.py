from dataclasses import dataclass


@dataclass(frozen=True)
class AIInterviewQuestion:
    key: str
    category: str
    question: str
    interviewer_is_testing: str
    strong_answer_points: tuple[str, ...]
    follow_ups: tuple[str, ...]


AI_ASSISTED_INTERVIEW_QUESTIONS = (
    AIInterviewQuestion(
        key="ai-coding-workflow",
        category="Workflow and judgement",
        question="How do you use AI while coding?",
        interviewer_is_testing=(
            "Whether you use AI deliberately, remain responsible for the result, "
            "and can describe a repeatable workflow."
        ),
        strong_answer_points=(
            "Start with the problem, repository and expected behaviour.",
            (
                "Use AI for focused investigation, alternatives or review rather "
                "than blind generation."
            ),
            "Inspect every suggestion and keep only changes you understand.",
            "Verify with tests, static checks, manual reasoning and a final diff review.",
            "Remain accountable for the code regardless of who or what suggested it.",
        ),
        follow_ups=(
            "What do you do yourself before asking AI for help?",
            "What context do you usually provide?",
            "Give an example where AI materially improved your speed.",
            "How do you stop AI from expanding the scope of the task?",
            "What does your final review look like?",
            "What do you do when you cannot explain part of the generated code?",
            "When do you stop prompting and solve the problem directly?",
        ),
    ),
    AIInterviewQuestion(
        key="when-to-use-ai",
        category="Workflow and judgement",
        question="How do you decide when AI is appropriate and when it is not?",
        interviewer_is_testing=(
            "Your ability to match the tool to the risk, uncertainty and value of the task."
        ),
        strong_answer_points=(
            "Consider task risk, available context, reversibility and verification cost.",
            (
                "Use AI readily for explanation, exploration, test ideas and "
                "repetitive transformations."
            ),
            (
                "Apply more caution to security, authentication, money, privacy "
                "and destructive operations."
            ),
            "Do not share protected data or use a tool that conflicts with company policy.",
            "Avoid AI when checking the answer would cost more than solving the task directly.",
        ),
        follow_ups=(
            "What kinds of tasks do you commonly delegate to AI?",
            "Which tasks would you never delegate without close review?",
            "How does unfamiliarity with a technology affect your decision?",
            "Would you use AI differently under time pressure?",
            "How do you assess whether a change is reversible?",
            "When has AI made a simple task slower?",
            "How would company policy change your workflow?",
        ),
    ),
    AIInterviewQuestion(
        key="prompting-unfamiliar-repository",
        category="Workflow and judgement",
        question="How do you prompt AI when working in an unfamiliar repository?",
        interviewer_is_testing=(
            "Whether you investigate before editing and give the model enough grounded context."
        ),
        strong_answer_points=(
            "Begin with the task, failing behaviour and relevant repository structure.",
            "Ask for explanation and execution tracing before requesting code changes.",
            (
                "Provide focused files, tests, versions and constraints rather "
                "than dumping everything."
            ),
            "Ask the model to identify assumptions and evidence for likely root causes.",
            "Keep the requested output narrow and reviewable.",
        ),
        follow_ups=(
            "What would your first prompt contain?",
            "Why ask for explanation before asking for a fix?",
            "How do you decide which files to include?",
            "What do you do when the model asks for more context?",
            "How do you prevent it from inventing repository behaviour?",
            "How would you prompt when several tests fail?",
            "What is wrong with the prompt 'Fix this repository'?",
            "How do your prompts change after you discover the root cause?",
        ),
    ),
    AIInterviewQuestion(
        key="verify-ai-code",
        category="Verification and debugging",
        question="How do you verify that AI-generated code is correct?",
        interviewer_is_testing=(
            "Whether your verification goes beyond seeing one green test or "
            "trusting plausible code."
        ),
        strong_answer_points=(
            "Compare the change with the requirement and existing behaviour.",
            "Run the smallest relevant test first, then the full suite.",
            "Check edge cases, error paths, types, linting and the final diff.",
            (
                "Confirm APIs and library behaviour against the installed version "
                "or official documentation."
            ),
            "Explain the code in your own words before accepting it.",
        ),
        follow_ups=(
            "What happens when the existing tests are incomplete?",
            "How do you detect a plausible but incorrect solution?",
            "How do you verify that unrelated behaviour was not broken?",
            "What security checks would you add?",
            "Would passing tests ever be insufficient?",
            "How do you verify performance-sensitive code?",
            "What do you do if the code works but is difficult to understand?",
            "How do you review a large generated diff?",
        ),
    ),
    AIInterviewQuestion(
        key="debug-failing-tests-with-ai",
        category="Verification and debugging",
        question="How do you use AI to investigate failing tests?",
        interviewer_is_testing=(
            "Whether you can use AI to reason from evidence rather than patch symptoms."
        ),
        strong_answer_points=(
            "Run the suite and read every failing assertion before prompting.",
            "Trace the expected and actual values through the existing code.",
            "Ask for ranked root-cause hypotheses supported by repository evidence.",
            "Fix the smallest underlying issue and run the targeted test.",
            "Run the full suite and review the diff before moving on.",
        ),
        follow_ups=(
            "What if several assertions fail in one test?",
            "How do you distinguish a root cause from a symptom?",
            "What if the test itself appears wrong?",
            "What if fixing one test causes another to fail?",
            "How do you handle a misleading error message?",
            "What would you ask AI after your first hypothesis fails?",
            "How do you avoid changing production code merely to satisfy a brittle test?",
            "How would you manage this workflow in a timed assessment?",
        ),
    ),
    AIInterviewQuestion(
        key="accept-edit-reject",
        category="Verification and debugging",
        question="Tell me about an AI suggestion you accepted, changed or rejected.",
        interviewer_is_testing=(
            "Your technical judgement and whether you treat AI output as a "
            "proposal rather than authority."
        ),
        strong_answer_points=(
            "Describe the concrete task and the suggestion.",
            "Explain the evidence used to evaluate it.",
            "State exactly what you accepted, edited or rejected.",
            "Explain the risk or trade-off behind the decision.",
            "Show how the final result was verified.",
        ),
        follow_ups=(
            "What was technically wrong with the rejected part?",
            "Have you rejected code that passed the visible tests?",
            "How did you discover the issue?",
            "What alternative did you implement?",
            "Did the model introduce unnecessary abstraction?",
            "Did it assume an API or dependency that did not exist?",
            "What would have happened if you accepted the suggestion unchanged?",
            "What did the experience change about your later prompts?",
        ),
    ),
    AIInterviewQuestion(
        key="hallucinated-apis",
        category="Verification and debugging",
        question="How do you prevent AI from inventing APIs, dependencies or repository behaviour?",
        interviewer_is_testing=(
            "Whether you verify external facts and stay grounded in the actual codebase."
        ),
        strong_answer_points=(
            "Provide installed versions, lockfiles and relevant interfaces.",
            "Search the repository before accepting claims about existing helpers or conventions.",
            "Check official documentation for version-specific behaviour.",
            "Avoid new dependencies unless they are justified and permitted.",
            "Run a small executable check when documentation or memory is ambiguous.",
        ),
        follow_ups=(
            "How do you check whether a suggested method exists in the installed version?",
            "What if the model cites documentation you cannot find?",
            "How do lockfiles help?",
            "Would you let AI add a new dependency during an assessment?",
            "How do you verify a suggested database or framework feature?",
            "What if the repository already has a helper that the model overlooked?",
            "How do you handle deprecated APIs?",
        ),
    ),
    AIInterviewQuestion(
        key="tests-are-incomplete",
        category="Verification and debugging",
        question=(
            "What do you do when AI-generated code passes the tests but the tests "
            "are incomplete?"
        ),
        interviewer_is_testing=(
            "Whether you can reason about correctness independently of the supplied test suite."
        ),
        strong_answer_points=(
            "Derive expected invariants and boundaries from the requirement.",
            "Add focused tests for error paths, boundaries and previously uncovered behaviour.",
            "Manually trace representative inputs through the code.",
            "Review interactions with callers, persistence and external systems.",
            "State remaining uncertainty instead of overstating confidence.",
        ),
        follow_ups=(
            "How do you identify missing test cases?",
            "Which boundary cases do you check first?",
            "How would you test a function with many input combinations?",
            "What if adding tests is outside the assessment instructions?",
            "How do you validate integration behaviour without a full environment?",
            "When would you use mocks and when would you avoid them?",
            "How do you communicate remaining limitations?",
        ),
    ),
    AIInterviewQuestion(
        key="privacy-security-and-ip",
        category="Risk, privacy and quality",
        question="How do you use AI without exposing private code, credentials or customer data?",
        interviewer_is_testing=(
            "Whether you understand that AI use is also a security, privacy and policy decision."
        ),
        strong_answer_points=(
            "Follow the organisation's approved-tool and data-handling policies.",
            "Never include secrets, credentials or unnecessary personal data.",
            "Minimise and anonymise context where permitted.",
            "Understand retention, training and access settings before using a tool.",
            "Stop and ask when ownership or confidentiality is unclear.",
        ),
        follow_ups=(
            "What information would you never paste into a public AI tool?",
            "How would you anonymise a production error?",
            "What do you do if a useful prompt requires customer data?",
            "How do environment variables and secret managers help?",
            "What if a colleague shares sensitive code with an unapproved tool?",
            "How would you handle proprietary repository code in an interview assessment?",
            "What is the difference between minimising context and removing necessary context?",
            "How do prompt-injection risks apply to repository content?",
        ),
    ),
    AIInterviewQuestion(
        key="security-review",
        category="Risk, privacy and quality",
        question="How do you review AI-assisted code for security problems?",
        interviewer_is_testing=(
            "Whether security remains an explicit review dimension instead of an afterthought."
        ),
        strong_answer_points=(
            "Identify trust boundaries, inputs, outputs and privileged operations.",
            "Check validation, authentication, authorisation and error handling.",
            "Look for injection, unsafe deserialisation, leaked secrets and insecure defaults.",
            "Review dependencies and configuration as well as application code.",
            "Use automated checks as support, not as proof of safety.",
        ),
        follow_ups=(
            "What would you inspect in an AI-generated REST endpoint?",
            "How do authentication and authorisation differ?",
            "How would you check for SQL injection?",
            "What could go wrong with generated error messages?",
            "How do you review dependency changes?",
            "Would you trust AI to generate cryptographic code?",
            "What security tests would you add?",
        ),
    ),
    AIInterviewQuestion(
        key="avoid-dependence",
        category="Risk, privacy and quality",
        question="How do you avoid becoming dependent on AI or losing your own understanding?",
        interviewer_is_testing=(
            "Whether AI strengthens your engineering ability rather than replacing it."
        ),
        strong_answer_points=(
            "Attempt to frame and trace the problem before requesting help.",
            "Use AI to challenge reasoning, explain unfamiliar code or compare alternatives.",
            "Rewrite or simplify suggestions until they match your understanding.",
            "Practise important skills without AI and notice where fluency is weakening.",
            "Be able to continue when the tool is unavailable.",
        ),
        follow_ups=(
            "How do you know when you are relying on AI too much?",
            "Do you ever solve tasks without AI deliberately?",
            "What do you do when AI gives an answer faster than you can understand it?",
            "How do you retain what you learned from an AI-assisted task?",
            "Which fundamentals should remain strong without assistance?",
            "How would you work if AI became unavailable during an assessment?",
            "Can AI make junior developers weaker?",
        ),
    ),
    AIInterviewQuestion(
        key="ai-code-review",
        category="Ownership and communication",
        question="How do you use AI during code review?",
        interviewer_is_testing=(
            "Whether you can use AI as a second reviewer while preserving human "
            "judgement and context."
        ),
        strong_answer_points=(
            "Give the model the requirement, relevant diff and repository conventions.",
            "Ask for concrete risks, missed cases and questions rather than a generic approval.",
            "Verify every comment against the code and expected behaviour.",
            "Prioritise correctness and maintainability over stylistic churn.",
            "Keep the human author and reviewer accountable for the final decision.",
        ),
        follow_ups=(
            "What prompt would you use to review a diff?",
            "How do you handle false-positive review comments?",
            "Can AI understand product context well enough to review code?",
            "How do you stop it from suggesting unrelated refactors?",
            "Would you disclose AI-generated review comments?",
            "What should a human reviewer notice that AI may miss?",
            "How do you review tests generated alongside the code?",
        ),
    ),
    AIInterviewQuestion(
        key="document-ai-use",
        category="Ownership and communication",
        question="How do you communicate or document your use of AI?",
        interviewer_is_testing=(
            "Whether you are transparent, concise and able to explain your own contribution."
        ),
        strong_answer_points=(
            "State what AI was used for and what context was provided.",
            "Separate suggestions accepted, modified and rejected.",
            "Describe the verification performed.",
            "Record limitations or unresolved uncertainty.",
            "Follow the disclosure expectations of the team or assessment.",
        ),
        follow_ups=(
            "What would you include in an AI-use note?",
            "How detailed should the prompt history be?",
            "Would you mention AI use in a pull request?",
            "How do you distinguish your contribution from the tool's contribution?",
            "What if an interviewer assumes AI completed the whole task?",
            "How do you explain code that AI initially suggested?",
            "When might disclosure be mandatory?",
        ),
    ),
    AIInterviewQuestion(
        key="timed-assessment",
        category="Assessment and pairing",
        question="How would you use AI in a timed repository assessment?",
        interviewer_is_testing=(
            "Whether you can use the tool efficiently without surrendering "
            "control of the assessment."
        ),
        strong_answer_points=(
            "Run tests and inspect the task before opening a broad AI conversation.",
            "Use short, evidence-based prompts tied to the current failure or feature.",
            "Timebox investigation and keep changes small.",
            "Run targeted tests, then the full suite, and review the final diff.",
            "Leave time to document AI use and explain every decision.",
        ),
        follow_ups=(
            "What would you do in the first five minutes?",
            "How much time would you spend prompting before changing approach?",
            "Would you ask AI to implement the feature immediately?",
            "How do you recover from an unhelpful AI direction?",
            "How do you divide time between fixing tests and adding the feature?",
            "What do you include in the final AI-use note?",
            "How do you behave if the tool becomes unavailable?",
            "What would you say while pair programming after the assessment?",
        ),
    ),
    AIInterviewQuestion(
        key="measure-ai-value",
        category="Assessment and pairing",
        question="How do you know whether AI is actually improving your engineering work?",
        interviewer_is_testing=(
            "Whether you evaluate AI by outcomes rather than novelty or the "
            "amount of generated code."
        ),
        strong_answer_points=(
            "Compare cycle time, defect rate, rework and review effort.",
            "Look for faster understanding and better test coverage, not only faster typing.",
            "Notice tasks where prompting and correction exceed the saved effort.",
            "Assess whether the resulting code remains maintainable by the team.",
            "Use concrete examples instead of claiming a universal productivity increase.",
        ),
        follow_ups=(
            "Which metric matters most to you?",
            "Can AI make you faster while reducing quality?",
            "Tell me about a task where AI slowed you down.",
            "How do you measure rework caused by a bad suggestion?",
            "How would a team evaluate AI-assisted development?",
            "Does more generated code mean more productivity?",
            "How do maintainability and knowledge sharing affect the calculation?",
        ),
    ),
)


AI_INTERVIEW_QUESTION_BY_KEY = {
    question.key: question for question in AI_ASSISTED_INTERVIEW_QUESTIONS
}
