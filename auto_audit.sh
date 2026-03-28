#!/bin/bash
# Claude Code version of auto_audit.sh
# to kill the process: `pkill -9 -f "/bin/bash ./auto_audit.sh --task all"`

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOLVER="$REPO_ROOT/scripts/resolve_task_dirs.py"

usage() {
  cat <<EOF
Usage: $(basename "$0") [--task <spec>] [--start_from <task_id>] | [<path>]

  --task, -t   Task spec (same as evaluation/run_evaluate_parallel.py --task):
               all | category_N | category_N_MM | CategoryN_.../S_XX | tasks/...
  --start_from Start from a task id within the resolved set (e.g. S_03, K_02).
               Useful when --task expands to multiple tasks (e.g. category_1).
  <path>       Legacy: tasks/Category1_Statics_Equilibrium/S_01

Examples:
  $(basename "$0") --task category_1_01
  $(basename "$0") --task category_1 --start_from S_03
  $(basename "$0") --task all
  $(basename "$0") tasks/Category1_Statics_Equilibrium/S_01
EOF
}

TASK_SPEC=""
START_FROM=""
while [ $# -gt 0 ]; do
  case "$1" in
    -t|--task)
      [ -n "${2:-}" ] || { echo "Missing value for $1" >&2; exit 1; }
      TASK_SPEC="$2"
      shift 2
      ;;
    --start_from)
      [ -n "${2:-}" ] || { echo "Missing value for $1" >&2; exit 1; }
      START_FROM="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [ -n "$TASK_SPEC" ]; then
        echo "Unexpected argument: $1" >&2
        usage >&2
        exit 1
      fi
      TASK_SPEC="$1"
      shift
      ;;
  esac
done

if [ -z "$TASK_SPEC" ]; then
  usage >&2
  exit 1
fi

TASK_DIRS=()
while IFS= read -r rel; do
  [ -z "$rel" ] && continue
  TASK_DIRS+=("$REPO_ROOT/$rel")
done < <(cd "$REPO_ROOT" && python3 "$RESOLVER" "$TASK_SPEC") || exit 1

if [ ${#TASK_DIRS[@]} -eq 0 ]; then
  echo "No task directories resolved for: $TASK_SPEC" >&2
  exit 1
fi

if [ -n "$START_FROM" ]; then
  if ! [[ "$START_FROM" =~ ^[A-Za-z]_[0-9]{2}$ ]]; then
    echo "Invalid --start_from value: $START_FROM (expected format like S_03 or K_02)" >&2
    exit 1
  fi
  FILTERED_TASK_DIRS=()
  SEEN_START=0
  for dir in "${TASK_DIRS[@]}"; do
    task_id=$(basename "$dir")
    if [ "$SEEN_START" -eq 0 ] && [ "$task_id" = "$START_FROM" ]; then
      SEEN_START=1
    fi
    if [ "$SEEN_START" -eq 1 ]; then
      FILTERED_TASK_DIRS+=("$dir")
    fi
  done
  if [ "$SEEN_START" -eq 0 ]; then
    echo "--start_from $START_FROM was not found in resolved tasks for spec: $TASK_SPEC" >&2
    exit 1
  fi
  TASK_DIRS=("${FILTERED_TASK_DIRS[@]}")
fi

# ==========================================
# MODEL CONFIGURATION
# ==========================================
# Model configuration
MODELS=("MiniMax-M2.7")

# Global variable to track models that have failed (quota or crash) during this run
BLACKLISTED_MODELS=""

# When claude exits non-zero: print why-it-failed hints (never prints secret values).
print_claude_failure_diagnostics() {
    local exit_code="$1"
    local model="$2"
    local prompt_bytes="$3"
    local stderr_file="$4"
    local stdout_file="$5"

    echo "  [🔍] -------- Claude Code failure diagnostics --------" >&2
    echo "  [🔍] exit_code=$exit_code model=$model prompt_bytes=$prompt_bytes" >&2
    echo "  [🔍] invocation: claude -p --model \"$model\" -p \"<prompt ${prompt_bytes} bytes>\"" >&2
    echo "  [🔍] cwd=$(pwd)" >&2
    echo "  [🔍] shell: $BASH_VERSION" >&2

    local cbin
    cbin=$(command -v claude 2>/dev/null || true)
    if [ -n "$cbin" ]; then
        echo "  [🔍] claude binary: $cbin" >&2
        _cv=$(timeout 8 claude -v 2>&1 | tr '\n' ' ' || true)
        echo "  [🔍] claude -v: ${_cv:-<failed>}" >&2
    else
        echo "  [🔍] claude binary: NOT FOUND in PATH" >&2
    fi

    for var in ANTHROPIC_API_KEY; do
        eval "v=\${$var:-}"
        if [ -n "$v" ]; then
            echo "  [🔍] $var is SET (length ${#v} chars)" >&2
        else
            echo "  [🔍] $var is UNSET" >&2
        fi
    done

    for p in HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY NO_PROXY no_proxy; do
        eval "pv=\${$p:-}"
        if [ -n "$pv" ]; then
            echo "  [🔍] $p is set (length ${#pv})" >&2
        fi
    done

    local sb sse
    sb=$(wc -c < "$stdout_file" 2>/dev/null | tr -d ' ' || echo 0)
    sse=$(wc -c < "$stderr_file" 2>/dev/null | tr -d ' ' || echo 0)
    echo "  [🔍] captured stdout_bytes=$sb stderr_bytes=$sse" >&2

    if command -v curl >/dev/null 2>&1; then
        _curl_out=$(curl -sS -m 6 -o /dev/null -w "%{http_code}" "https://www.google.com" 2>&1) || _curl_out="curl_error:${_curl_out}"
        echo "  [🔍] connectivity: https://www.google.com -> ${_curl_out}" >&2
    else
        echo "  [🔍] connectivity: (curl not installed; skipped)" >&2
    fi

    if [ "${AUTO_AUDIT_VERBOSE:-0}" = "1" ]; then
        echo "  [🔍] AUTO_AUDIT_VERBOSE=1: env names containing ANTHROPIC/PROXY (values hidden):" >&2
        env | grep -iE '^(ANTHROPIC|HTTP_|HTTPS_|ALL_|NO_)' | while IFS= read -r line; do
            name="${line%%=*}"
            echo "  [🔍]   ${name}=<hidden>" >&2
        done || true
    fi
    echo "  [🔍] Tip: AUTO_AUDIT_VERBOSE=1 ./auto_audit.sh ... for extra env listing" >&2
    echo "  [🔍] -----------------------------------------" >&2
}

# One-line plain-English hint from stderr
summarize_claude_stderr() {
    local f="$1"
    [ -f "$f" ] || return 0
    if grep -q 'overloaded_error\|429\|CAPACITY_EXHAUSTED' "$f" 2>/dev/null; then
        echo "  [📌] Plain summary: Anthropic API returned 429 — model is overloaded (transient). Retry later or try next model in fallback list." >&2
        return 0
    fi
    if grep -q 'invalid_request_error\|400' "$f" 2>/dev/null; then
        echo "  [📌] Plain summary: Bad request (400). Check API key and request format." >&2
        return 0
    fi
    if grep -qE '401|UNAUTHORIZED|invalid_api_key' "$f" 2>/dev/null; then
        echo "  [📌] Plain summary: Auth problem. Check ANTHROPIC_API_KEY." >&2
        return 0
    fi
}

claude_stderr_is_transient() {
    local f="$1"
    [ -f "$f" ] || return 1
    grep -qE 'overloaded_error|429|CAPACITY_EXHAUSTED' "$f" 2>/dev/null
}

# Return 0 if we should blacklist this model after failure; 1 if we should not.
claude_should_blacklist_model() {
    local model="$1"
    local errfile="$2"
    if claude_stderr_is_transient "$errfile"; then
        return 1
    fi
    return 0
}

# Function to run Claude Code with model fallback
run_claude_with_fallback() {
    local PROMPT_CONTENT="$1"
    local SUCCESS=false
    local OUTPUT=""

    for MODEL in "${MODELS[@]}"; do
        # Check if the model is in the blacklist
        if [[ " $BLACKLISTED_MODELS " =~ " $MODEL " ]]; then
            # Skip blacklisted models silently
            continue
        fi

        PROMPT_BYTES=${#PROMPT_CONTENT}
        echo "  [→] Calling Claude Code with model: $MODEL (prompt ~${PROMPT_BYTES} bytes)..." >&2
        echo "  [→] Started at $(date '+%Y-%m-%d %H:%M:%S %z') — headless \`claude -p\` runs the agent (tools/files); stdout is buffered until the CLI exits." >&2

        # Capture stdout and stderr separately
        TMP_ERR=$(mktemp)
        TMP_OUT=$(mktemp)
        API_START=$(date +%s)
        claude -p --model "$MODEL" --permission-mode dontAsk --system-prompt "You are a helpful assistant with access to tools for reading and modifying files. Use the available tools to complete the task." "$PROMPT_CONTENT" >"$TMP_OUT" 2>"$TMP_ERR"
        EXIT_CODE=$?
        API_END=$(date +%s)
        API_DURATION=$((API_END - API_START))
        OUTPUT=$(cat "$TMP_OUT")
        echo "  [→] API call finished after ${API_DURATION}s (exit code $EXIT_CODE) at $(date '+%H:%M:%S')" >&2

        if [ $EXIT_CODE -eq 0 ]; then
            SUCCESS=true
            rm -f "$TMP_ERR" "$TMP_OUT"
            break
        else
            echo "  [⚠️] Model $MODEL failed (exit $EXIT_CODE)." >&2
            summarize_claude_stderr "$TMP_ERR"
            print_claude_failure_diagnostics "$EXIT_CODE" "$MODEL" "$PROMPT_BYTES" "$TMP_ERR" "$TMP_OUT"

            LAST_RUN_DIR="${TMPDIR:-/tmp}/auto_audit_claude_last_run"
            mkdir -p "$LAST_RUN_DIR"
            cp -f "$TMP_ERR" "$LAST_RUN_DIR/stderr.txt"
            cp -f "$TMP_OUT" "$LAST_RUN_DIR/stdout.txt"
            echo "  [ℹ️] Full stdout/stderr saved to: $LAST_RUN_DIR/{stdout.txt,stderr.txt}" >&2

            if [ -s "$TMP_OUT" ]; then
                echo "  [ℹ️] claude stdout (errors sometimes appear here) — first 60 lines:" >&2
                OUT_LINES=$(wc -l < "$TMP_OUT")
                if [ "$OUT_LINES" -le 60 ]; then
                    sed 's/^/    | /' "$TMP_OUT" >&2
                else
                    sed -n '1,35p' "$TMP_OUT" | sed 's/^/    | /' >&2
                    echo "    | ... ($OUT_LINES lines total, truncated) ..." >&2
                    tail -n 25 "$TMP_OUT" | sed 's/^/    | /' >&2
                fi
            else
                echo "  [ℹ️] claude stdout: (empty)" >&2
            fi

            echo "  [ℹ️] claude stderr — full stream:" >&2
            ERR_LINES=$(wc -l < "$TMP_ERR")
            if [ "$ERR_LINES" -le 120 ]; then
                sed 's/^/    | /' "$TMP_ERR" >&2
            else
                echo "    | --- stderr (first 60 lines of $ERR_LINES) ---" >&2
                sed -n '1,60p' "$TMP_ERR" | sed 's/^/    | /' >&2
                echo "    | --- stderr (last 60 lines) ---" >&2
                tail -n 60 "$TMP_ERR" | sed 's/^/    | /' >&2
            fi

            if claude_should_blacklist_model "$MODEL" "$TMP_ERR"; then
                echo "  [🚫] Adding $MODEL to blacklist (skipped for the rest of this script run)." >&2
                BLACKLISTED_MODELS="$BLACKLISTED_MODELS $MODEL "
            else
                echo "  [ℹ️] Not blacklisting $MODEL — transient error; explicit models still apply on next try." >&2
            fi
            rm -f "$TMP_ERR" "$TMP_OUT"
        fi
    done

    if [ "$SUCCESS" = false ]; then
        echo "  [❌] FATAL ERROR: All models failed. Stopping loop." >&2
        rm -rf "$ORIGINAL_STATE_DIR" # Cleanup on fail
        exit 1
    fi

    # Echo the clean output back to the caller
    echo "$OUTPUT"
}

run_auto_audit_for_task() {
    local TASK_DIR ORIGINAL_STATE_DIR
    TASK_DIR="${1%/}"

    # ==========================================
    # SETUP REVISION TRACKING
    # ==========================================
    echo "📦 Backing up initial state for revision tracking..."
    ORIGINAL_STATE_DIR=$(mktemp -d)
    cp -r "$TASK_DIR/"* "$ORIGINAL_STATE_DIR/"

# ==========================================
# PROMPTS - aligned with .claude/skills/task-audit/SKILL.md
# ==========================================
read -r -d '' PROMPT << 'EOM'
# Objective
Conduct a strict audit of the task in the following directory: '${TASK_DIR}'. Use your tools to systematically list and read all relevant code files there. Your goal is to analyze the existing code for logic, consistency, and expected failure states, reporting any violations.

## STRICT RULE 1: FIX MODE ENABLED
You are acting as an auditor AND an engineer. Your final output must consist of your analysis, a comprehensive list of violation cases, AND you MUST use your tools to modify and fix ANY and ALL violations you find.

## STRICT RULE 2: ANTI-LAZINESS & EXHAUSTIVE COMPLETENESS (CRITICAL)
You must NOT stop after finding 1 or 2 errors. Do not provide "examples" of violations; you must provide an EXHAUSTIVE, line-by-line enumeration of EVERY SINGLE violation within this specific task directory (strictly referring to the module-level files inside `S_01`, such as `environment.py`, `evaluator.py`, `prompt.py`, etc.). To ensure completeness, you must mentally extract a full list of every physical parameter in `environment.py` and trace EACH ONE through every other module. Please perform the following audit steps for the `S_01` task directory:

### Step 1: Cross-Module Consistency Audit
Systematically review all modules within the `S_01` task directory (including `environment.py`, `evaluator.py`, `feedback.py`, `prompt.py`, `stages.py`, and `renderer.py`).
* **Expected Outcome:** All modules must be logically consistent and coherent. The physical mechanics and parameters defined in the underlying environment (especially in mutated tasks) MUST perfectly align with the evaluation logic and the prompt descriptions.
* **Action:** Document EVERY SINGLE discrepancy, logical conflict, or misaligned physics across these files. Trace every constant. No modification!

## Step 2: Information Consistency & Variable Audit
Carefully scrutinize how physical variables and constraints are handled across the modules. You must strictly adhere to the following definitions regarding "Constraint", "Visible", and "Invisible" variables:

### 1. Constraint Completeness (The "Constraint Variable" Rule)
* **Definition:** A "Constraint Variable" is ANY variable that defines an absolute maximum, minimum, or failure threshold required to logically or mathematically solve the task (e.g., maximum mass budgets, minimum target heights, force/torque limits for joints, time limits, or strict geometric boundaries). 
* **Audit Rule:** You must cross-reference `environment.py` and `evaluator.py` to ensure that **ALL necessary structural limits and boundaries** are explicitly stated in the initial prompt with their exact numerical values. **Crucially, this applies even if the limit is physically invisible to the naked eye** (e.g., an internal motor's maximum torque limit). Since these are required constraints for the agent to succeed, they MUST be explicitly prompted.
* **Exhaustive Check:** Scan `environment.py` for ANY hardcoded constraint numbers or limits. Verify they are correctly exposed in `prompt.py`. Document EVERY omission.

### 2. Mutation Synchronization (Updating "Constraint" & "Visible" Variables)
* **Definition:** A "Visible Variable" refers to observable physical properties or geometric setups explicitly mentioned in the prompt (e.g., gap width, target coordinates, initial mass).
* **Audit Rule:** If `stages.py` modifies ANY "Constraint Variable" OR "Visible Variable" that is mentioned in the prompt, the prompt string **MUST** be dynamically updated to reflect the new value while explicitly keeping a record of the old value.
* **Format Requirement:** The prompt update logic must strictly follow the format: `[new_value] (originally [old_value] in the source environment)`. You can refer to `@'tasks/Category1_Statics_Equilibrium/S_01/stages.py'`.
* **CRITICAL - Execution Verification:** Because these dynamic updates heavily rely on complex Regular Expressions (`regex`) or string replacements, you MUST NOT blindly trust the code. You must actively dry-run or conceptually execute EVERY SINGLE regex logic block in `stages.py` to ensure it successfully captures the target string and accurately outputs the exact required format. 
* *Example Check:* If a mass budget (Constraint) changes from 380kg to 200kg, the prompt must output: `200kg (originally 380kg in the source environment)`. Document ANY regex mismatches, failures to capture, or malformed string outputs.

### 3. Hidden Physics Protection (The "Invisible Variable" Rule)
* **Definition:** "Invisible Variables" are underlying environmental physical constants that are **NOT limits or constraints**, and cannot be directly observed by the naked eye (e.g., gravitational acceleration, global friction coefficients, wind force, earthquake amplitude/frequency).
* **Audit Rule:** The exact numerical values, magnitudes, or directions of change (e.g., "gravity increased to -25", "friction reduced") of these Invisible Variables **MUST NOT** be mentioned in the prompt under any circumstances. The agent is forced to infer these specific anomalies through physical interaction and feedback.
* **CRITICAL EXCEPTION:** Mentioning the mere *name* of the variable as a general warning is ONLY allowed within the `UNIFORM_SUFFIX` (see Sub-step 4 below). 
* **Action:** Check EVERY line of `prompt.py` and the regex outputs in `stages.py`. Document EVERY instance where an INVISIBLE environmental constant's specific value or explicit change direction is leaked.

### 4. The `UNIFORM_SUFFIX` Audit (The "Union" Rule)
* **Audit Rule:** The `UNIFORM_SUFFIX` (appended at the end of the prompt for mutated stages) MUST dynamically list the **UNION** of all physical variables that have been modified across Stage-1, Stage-2, Stage-3, and Stage-4 in `stages.py`.
* **Format & Tone Restriction:** The suffix must ONLY provide a general warning about *what* might have changed (e.g., "Gravitational acceleration: Vertical loads may be significantly different."). It MUST NEVER pinpoint the exact mutations, specific values, or directions of change for any specific stage. The ideal scenario is telling the model *what* variables might change, but never *how* they change.
* **Action:** Document EVERY instance where the `UNIFORM_SUFFIX` fails to include a modified variable from the union of all 4 stages, OR where it violates the tone by explicitly stating *how* a variable changes.

---
### ACTION REQUIRED based on your findings:
**Final Deliverable:** Provide an exhaustively detailed list of all violations categorized by the steps above. If a category has no violations, explicitly state "No violations found for [Category]". Do not summarize; be hyper-specific.

**CRITICAL FIXING STEP:** After listing violations, immediately fix all violations in this turn, but obey STRICT RULE 3. If a fix would change baseline physics/default thresholds, do not apply it; mark it as "requires manual product decision".
EOM

# ==========================================
# EXECUTION LOOP
# ==========================================
ITERATION=1
while true; do
    echo "========================================================"
    echo "🔄 Iteration $ITERATION: Running fresh audit on $TASK_DIR..."
    echo "========================================================"

    OUTPUT=$(run_claude_with_fallback "$PROMPT")

    echo "$OUTPUT"
    echo "========================================================"
    echo "🧠 Evaluating LLM Response for Completion Status..."

    read -r -d '' CLASSIFY_PROMPT << 'EOM'
Analyze the following report from a code auditor.
Did the auditor find ANY violations?
- If the auditor found ZERO violations and the code is perfectly clean (e.g., stated "No violations found" for all categories), reply with exactly the word "CLEAN".
- If the auditor found ANY violations (even if they fixed them), or if the report is ambiguous, reply with exactly the word "DIRTY".
Reply with NOTHING ELSE but that single word.

Report to analyze:
$OUTPUT
EOM

    CLASSIFICATION=$(run_claude_with_fallback "$CLASSIFY_PROMPT")
    CLASSIFICATION=$(echo "$CLASSIFICATION" | xargs)

    echo "Classification Result: [$CLASSIFICATION]"

    if [ "$CLASSIFICATION" = "CLEAN" ]; then
        echo "✅ Task $TASK_DIR is clean! Breaking loop."
        break
    else
        echo "⚠️  Violations detected or fixes applied. Wiping context and restarting..."
        ITERATION=$((ITERATION+1))
    fi
done

# ==========================================
# GENERATE LOG / DIFF
# ==========================================
echo "========================================================"
echo "📝 Generating revision patch log..."

# Strip 'tasks/' from the start of the path if it exists to get 'Category/Task'
REL_PATH=$(echo "$TASK_DIR" | sed 's|^tasks/||')
LOG_DIR="tasks/auto_audit_log/$REL_PATH"

# Ensure the log directory exists
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/revisions.patch"

# Diff the original state against the current state
# Ignore temporary pycache folders that might have been generated
diff -ruN -x "__pycache__" "$ORIGINAL_STATE_DIR" "$TASK_DIR" > "$LOG_FILE"

if [ -s "$LOG_FILE" ]; then
    echo "✅ Success: Revisions saved to $LOG_FILE"
else
    echo "ℹ️ No changes were made to the files during this audit."
    rm -f "$LOG_FILE"
fi

# Cleanup temp dir
rm -rf "$ORIGINAL_STATE_DIR"

# Generate HANDOFF.md for cross-session continuity
HANDOFF_FILE="$LOG_DIR/HANDOFF.md"
cat > "$HANDOFF_FILE" << EOF
# Audit Handoff: $(basename "$TASK_DIR")
## Timestamp: $(date '+%Y-%m-%d %H:%M:%S %z')
## Task: $TASK_DIR
## Spec: $TASK_SPEC
## Total Iterations: $ITERATION

## Last Run Status
$(if [ "$CLASSIFICATION" = "CLEAN" ]; then echo "Status: CLEAN - All violations fixed"; else echo "Status: DIRTY - Iterations completed"; fi)

## Log Files
- Revision patch: revisions.patch
EOF

echo "📋 Handoff file generated: $HANDOFF_FILE"
echo "========================================================"
}

for TASK_DIR in "${TASK_DIRS[@]}"; do
    echo "========================================================"
    echo "▶ Auto-audit task: $TASK_DIR  (spec: $TASK_SPEC, ${#TASK_DIRS[@]} total)"
    echo "========================================================"
    run_auto_audit_for_task "$TASK_DIR" || exit 1
done
