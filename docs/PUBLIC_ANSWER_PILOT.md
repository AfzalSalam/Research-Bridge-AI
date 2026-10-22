# Public answer pilot: incomplete runs

Date: 2026-10-20. Model: gemini-3.1-flash-lite. Prompts:
paper-cited-answer-v1 and paper-answer-support-v1.

The opt-in runner verifies both frozen public PDF hashes and page hashes before
network access, replays saved FTS/vector rankings with production hybrid fusion,
and supplies the top five exact excerpts. It uses no private documents, new
embeddings or database mutations. Maximum per full run: 12 questions and 24
provider calls. It stops on unavailable, preserves incremental results and refuses
to overwrite an existing output. Later runs record allowlisted per-stage errors.

## Observations

- v1: first question unavailable after 25,113 ms; stopped. Cause was not captured.
- A bounded generation-only diagnostic then validated a response for that question.
- v2: code-quality question answered and reviewed in 16,527 ms; parameter-selection
  question unavailable after 21,797 ms; stopped. Cause was not captured.
- The one returned claim says unit tests and static analysis support code quality.
  Its page-three quote explicitly names both. Agent audit: supported by that quote;
  not an independent human review. Source encoding includes replacement characters,
  retained exactly; source hashes match the frozen extraction.
- No unsupported-question results were reached. No aggregate answer accuracy,
  abstention rate, latency percentiles or citation-support rate can be reported.

Raw evidence: apps/api/evaluation/public-answer-pilot-v1.json and v2.json.
Both failed runs are retained; neither is labelled complete. Failures are not
counted as successful abstentions. Two papers with provisional labels would still
be too small for broad accuracy claims even after completion.

## Reproduction and next step

From apps/api, with public fixture PDFs present and GEMINI_API_KEY configured:
`uv run python -m scripts.run_answer_pilot --allow-public-text-to-gemini --output evaluation/public-answer-pilot-v3.json`

The runner now records safe per-stage outcomes to diagnose the interruption.
Do not repeatedly restart to select favourable outcomes. Investigate one bounded
failure with these diagnostics before completing the benchmark. No automatic
retry or provider fallback was added. Production generation remains unexposed;
consent, durable quotas and owner checks are still required before UI integration.


## Completed diagnostic run, 2026-10-21

Run v5 completed all 12 questions with 17 provider calls, prompt v2 and bounded
PDF typography alignment. Earlier v1-v4 and diagnostic artifacts remain preserved;
these are iterative development measurements on observed data, not a held-out test.

| Frozen category | Observed outcome |
| --- | --- |
| 8 answerable questions | 5 answered; 3 invalid-citation outputs rejected |
| 4 unsupported questions | 4 abstained; none answered |
| Provider-service failures in v5 | 0 |

The three rejected questions were scikit-learn grid selection, nearest neighbours,
and LIBLINEAR multiclass handling. Successful generation followed by rejection
before support review identifies citation resolution as the remaining failure stage.
It does not establish the precise text mismatch in those uncaptured candidates.

All five returned citations map exactly to their retrieved source intervals.
Agent audit: code quality, Elastic Net limitations, LR solver and package separation
claims are directly supported by their cited quotes. The cross-validation claim's
main finding is supported by its quote, but the description of C as a *penalty*
parameter is defined in a different retrieved page-two excerpt that was not cited.
Thus four claims have complete cited support; one needs an additional citation for
that qualifier. This is a provisional agent audit, not independent human grading.
The separate model reviewer accepted that fifth claim, demonstrating its limits.

Nearest-rank latency across all 12 outcomes: p50 3,436.50 ms, p95 12,324.19 ms.
This includes generation/review/validation, excludes the six-second inter-question
pause and prior retrieval, and has too few samples for production latency claims.
52 focused tests passed before the final runner-policy test; full backend alignment
suite: 335 passed, one opt-in PostgreSQL test skipped. Final runner tests: 3 passed.
Ruff and mypy passed. No frontend code or API was changed.

Next: use server-defined citation choices to reduce quotation-copy failures and
require every factual qualifier to have cited support, then evaluate on additional
unseen papers. Keep generation unexposed until consent, durable quotas and owner
checks are integrated. Do not advertise general accuracy from this small pilot.


## Citation-choice evaluation, 2026-10-21

Server-defined citations (paper-citation-choices-v1, reviewer v2) were evaluated in
v6 and a separately saved continuation covering only the five unattempted questions.
The original 25-second generation timeout for LIBLINEAR solver remains a failure;
it was not retried or replaced. Across the two artifacts: all 12 distinct questions
attempted, 7/8 answerable questions answered, 1 timeout, 4/4 unsupported questions
abstained. No citation-copy/unknown-choice failure occurred. This is a development
comparison on the same small corpus, not measured general accuracy.

Every returned quote was checked against its saved exact source interval. Agent
review found the main findings supported, but the validation answer still calls C
a penalty parameter without citing the page-two definition. Reviewer v2 accepted
it. Consequently full factual citation support is NOT solved by this change.
The multiclass answer also reconstructs an extracted function name as train_one();
the identifier spelling was not independently verified against source code.
Server-supplied slices contain more surrounding text and sometimes cut sentences;
this is a usability limitation to address before presenting them in the reader.

Validation: 341 backend tests passed; one optional PostgreSQL integration test
skipped. Ruff and mypy passed (148 source files). Added catalog/materialization
and transport tests. No frontend/API changes, new dependencies or private data use.

Next: constrain support checking to selected citations, test uncited qualifiers
explicitly, and evaluate on unseen papers. Consent, durable generation quotas and
owner checks remain prerequisites for app integration. The live UI stays unchanged.


### Isolated support and context gates (2026-10-21)
Changed answers.py so the first review receives only the question, claims and their
selected citations. After support passes, a separate context-veto review receives
retrieved excerpts to detect contradictions or omitted qualifications. Either
negative, uncertain, malformed or failed review prevents an answer. Both stages
remain inside the original 60-second total deadline; each transport retains its
existing timeout. Maximum successful question cost is now three provider calls;
a complete 12-question pilot can use up to 36. No automatic retry was added.

Prompts: support v3 and context v1. The pilot records both versions. Fixture tests
prove uncited excerpts are excluded from the support payload and a failed support
review short-circuits context review; a context veto still suppresses the answer.
Files: apps/api/app/documents/answers.py, answer_prompts.py,
apps/api/scripts/run_answer_pilot.py, apps/api/tests/test_document_answers.py.

Live public regression: reviewer v3 still marked the previously uncited 'penalty'
qualifier supported, and also supported the version with that qualifier removed.
Evidence: apps/api/evaluation/isolated-support-review-v1.json. This is one negative
and one positive diagnostic, not an accuracy benchmark. Isolation did not solve
this semantic-review failure. Keep this negative example as a regression case;
do not treat model review as a guarantee or enable the answer UI on this evidence.
Next: compare a different review strategy/model against frozen positive/negative
support labels, then use unseen papers to assess generalization. Production
consent, durable quotas and owner rechecks still remain outstanding.

Validation for isolated-review increment: 343 backend tests passed, one optional PostgreSQL test skipped; 60 focused tests passed; Ruff and mypy passed (148 files). Live qualifier negative regression failed as documented; UI remains disabled.

Synthetic review comparison v1: aborted on first unavailable response; no accuracy comparison. The labelled fixture is preserved for a later run. Generation reservation groundwork does not resolve semantic-review reliability.
