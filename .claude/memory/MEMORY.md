# User Memory Index

This directory contains persistent user preferences and corrections for the SEED-Bench project.

## When to Read Which File

| File | When to Read | Why |
|------|-------------|-----|
| `user_preferences.md` | New project session, modifying workflow | Project org rules, code style, harness vs benchmark distinction |
| `shared_audit_rules.md` | Before running auto_audit.sh or auto_feedback.sh; when auditing variable classification | Constraint > Visible > Invisible rules, UNIFORM_SUFFIX, _CE mode |

## Files

- `user_preferences.md` — project org rules, code style, harness preferences, what NOT to do
- `shared_audit_rules.md` — task audit variable classification and evaluation mode rules
