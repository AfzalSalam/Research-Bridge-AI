# Research Bridge AI — Start Here

1. Copy this pack into the root of the Git repository.
2. Open Codex in the repository root.
3. Paste the prompt under **Prompt 0** in `CODEX_PROMPTS.md`.
4. Approve the audit and execution plan before implementation.
5. Run only one numbered phase at a time.
6. After every phase, paste **Review Gate**.
7. Inspect the diff, run the app, and commit before the next phase.

## Sources of truth

- Code: GitHub repository
- Product requirements: `PROJECT_SPEC.md`
- Engineering rules: `AGENTS.md`
- Roadmap: `ROADMAP.md`
- API contract: FastAPI OpenAPI output
- Database schema: Alembic migrations
- Approved visual design: Figma, when available

Do not allow multiple AI tools to regenerate the whole project independently.
Do not start the next phase until the current phase's tests and build pass.
