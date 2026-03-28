---
name: user_project_preferences
description: Project organization rules, code style, and harness engineering notes (git cleanup now in CLAUDE.md)
type: feedback
---

## Project Organization Rules

- Benchmark internal: `evaluation/`, `tasks/`, `methods/`, `common/`
- Harness improvements: `.claude/`
- **Never** modify `evaluation/prompt.py`, `evaluation/evaluate.py` etc. with harness improvements

## .claude/ Structure
- `CLAUDE.md` — project overview, running commands, **git session management (including pre-cleanup steps)**
- `skills/` — skill definitions
- `settings.local.json` — CLI permissions
- `memory/` — persistent memory

## Harness Engineering Preferences

### Implemented
- Context Compaction Priority in CLAUDE.md
- HANDOFF.md generation in auto_audit/feedback
- Sprint-contract and evaluator-tuning skills

### Rejected
- FeatureList.json generator — too complex
- run_audit_loop.py and task_linter.py — not in actual workflow

## Code Style Rules
- **No silent exception handling** — expose actual error, stop
- **Minimal comments** — only non-obvious logic

## What NOT to Do
- Don't add harness improvements to `evaluation/`
- Don't use try/except pass or broad catches
- Claude Code settings belong in `.claude/settings.local.json`
