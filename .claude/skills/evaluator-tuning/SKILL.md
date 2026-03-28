# Evaluator Tuning — Calibrating QA Strictness

## The Problem

From Anthropic's harness research: **"Claude is a poor QA agent — it identifies legitimate issues then talks itself into deciding they're not a big deal."**

This shows up as:
1. Finding a real bug, then concluding "it's minor, acceptable"
2. Testing surface cases, missing edge cases
3. Grading generously because the output came from an LLM

## The Solution: Hard Thresholds + Calibration Examples

### Principle 1: Hard Thresholds

Never accept "close enough." Every criterion has a hard pass/fail line:

```
❌ FAIL — Tool only places tiles at drag start/end points instead of filling the region.
   fillRectangle function exists but isn't triggered on mouseUp.

❌ FAIL — Delete key handler requires both selection AND selectedEntityId.
   Clicking an entity only sets selectedEntityId. Should be: selection || selectedEntityId.
```

### Principle 2: Specific Bug Reports, Not Vague Concerns

Bad: "There are some UI issues."
Good: "The rect fill tool doesn't fill — it only places tiles at corners."

Bad: "Audio could be improved."
Good: "Audio recording is stub-only (button toggles but no mic capture)."

### Principle 3: Feature Completeness vs Display-Only

From the DAW example: "several core DAW features are display-only without interactive depth."

This is a FAIL even if the UI looks polished:
- ❌ "Knobs are displayed but don't change audio parameters"
- ❌ "EQ curve shown but sliders don't affect sound"
- ❌ "Transport controls visible but don't respond"

## Calibration Examples

### Example 1: Stub Detection

**What a stub looks like:**
- Button toggles but does nothing functional
- UI element visually present but non-interactive
- Function exists in code but returns hardcoded values

**How to catch it:**
1. Try to use the feature
2. Verify the underlying data/API actually changes
3. Check for hardcoded return values in the code

### Example 2: Edge Case Erosion

**Starting state:** Agent tests the happy path.
**Problem:** Edge cases fail silently.

**Fix:** Explicitly test:
- Empty state (no data loaded)
- Boundary values (first/last item, min/max values)
- Error conditions (invalid input)

### Example 3: "Good Enough" Self-Deception

**What it sounds like:**
- "The layout is a bit off but it's functional"
- "The feature kind of works"
- "Minor issues but overall OK"

**Reality check:** If you had to write the spec yourself, would you accept this?

## Hard Rules for QA in SEED-Bench

When evaluating a task solution:

1. **Every constraint in prompt.py MUST be enforced.** If max_mass=2000kg and solution has 2001kg → FAIL
2. **Every feature in success_criteria MUST work end-to-end.** If "vehicle reaches x=30m" requires wheels to spin, and wheels don't spin → FAIL
3. **No "good enough" passes.** If 95% of the solution is there but 5% is stubbed → FAIL
4. **Specific failure reports only.** "Feature X doesn't work" with exact location and behavior, not vague concerns

## Interaction with Other Skills

- Use with `sprint-contract` to ensure the contract's verification criteria are specific enough
- Use with `feedback-refactor` to ensure feedback is diagnostic, not advisory
- Use with `forensic-failure-analysis` when root cause is unclear and you need deeper investigation
