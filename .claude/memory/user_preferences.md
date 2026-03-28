---
name: user_project_preferences
description: User corrections about SEED-Bench project organization and harness engineering
type: feedback
---

## Project Organization Rules

### Benchmark code vs harness code
- Benchmark internal code lives in `evaluation/`, `tasks/`, `methods/`, `common/`
- Harness/engineer improvements (things that help Claude Code work better) live in `.claude/`
- **IMPORTANT**: Never modify `evaluation/prompt.py`, `evaluation/evaluate.py`, etc. with harness improvements — those are benchmark internals

### .claude/ structure
- `.claude/CLAUDE.md` — project overview and running commands
- `.claude/skills/` — skill definitions for Claude Code to use
- `.claude/settings.local.json` — CLI permissions and local config
- `.claude/memory/` — user-level persistent memory (this directory)

## Harness Engineering Preferences

### Implemented improvements
1. **Context Compaction Priority** — added to CLAUDE.md to prevent architectural amnesia
2. **HANDOFF.md generation** — auto_audit.sh and auto_feedback.sh now generate handoff files
3. **Sprint Contract skill** — `.claude/skills/sprint-contract/SKILL.md`
4. **Evaluator Tuning skill** — `.claude/skills/evaluator-tuning/SKILL.md`

### Rejected ideas
- FeatureList.json generator — too complex, not通用 enough for SEED-Bench's diverse task types
- run_audit_loop.py and task_linter.py — not integrated into actual workflow, created but unused

## CLI Commands for this project
- Run audit: `./auto_audit.sh --task <spec>`
- Run feedback: `./auto_feedback.sh --task <spec>`
- Single task test: `python tasks/<Category>/<Task>/test_agent.py`
- Parallel evaluation: `python evaluation/run_evaluate_parallel.py --task <spec> --model-type <type> --model-name <name> --method <method>`

## Code Style Rules
- **No fallback on exceptions** — report detailed error and stop; do not silently catch and continue
- **Minimal comments** — only explain non-obvious logic; use succinct language, not prose

## What NOT to do
- Don't add harness improvements to `evaluation/` directory
- Don't create scripts that aren't integrated into actual workflow
- Claude Code settings belong in `.claude/settings.local.json`, not in `evaluation/`
- Don't use try/except pass or broad catches — always expose the actual error
