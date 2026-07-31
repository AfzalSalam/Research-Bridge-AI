# Research Bridge AI — Start Here

1. Open Codex in the repository root.
2. Read `AGENTS.md`, `PROJECT_SPEC.md`, `ROADMAP.md`, and the active plan.
3. Confirm the current Git status and preserve unrelated work.
4. Use the matching phase prompt from `CODEX_PROMPTS.md` as an execution aid.
5. Run only one approved numbered phase at a time.
6. After every phase, use **Review Gate**.
7. Inspect the full diff, run applicable checks, update the learning log, and
   create a clear commit before the next phase.

## Sources of truth

- Code: GitHub repository
- Product requirements: `PROJECT_SPEC.md`
- Engineering rules: `AGENTS.md`
- Roadmap: `ROADMAP.md`
- Current execution details: active approved file under `docs/plans/`
- API contract: FastAPI OpenAPI output
- Database schema: Alembic migrations
- Approved visual design: Figma, when available

Do not allow multiple AI tools to regenerate the whole project independently.
Do not start the next phase until the current phase's tests and build pass.
When a prompt conflicts with the engineering rules, product specification,
roadmap, or active plan, update the prompt instead of following stale text.
