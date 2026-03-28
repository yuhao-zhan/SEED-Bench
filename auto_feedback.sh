#!/bin/bash
# Claude Code version of auto_feedback.sh
# Phase 1: Forensic Analysis
# Phase 2: Feedback Optimization (uses Phase 1 results)
# Phase 3: QA Audit

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOLVER="$REPO_ROOT/scripts/resolve_task_dirs.py"

usage() {
  cat <<EOF
Usage: $(basename "$0") [--task <spec>] [--start_from <task_id>] | [<path>]

  --task, -t   Task spec (same as evaluation/run_evaluate_parallel.py --task):
               all | category_N | category_N_MM | CategoryN_.../S_XX | tasks/...
  --start_from Start from a task id within the resolved set (e.g. S_03, K_02).
  <path>       Legacy: tasks/Category1_Statics_Equilibrium/S_06

Examples:
  $(basename "$0") --task category_1_01
  $(basename "$0") --task category_1 --start_from S_03
  $(basename "$0") --task all
  $(basename "$0") tasks/Category1_Statics_Equilibrium/S_06
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
MODELS=("MiniMax-M2.7")
BLACKLISTED_MODELS=""

HEARTBEAT_PIDS=""

register_heartbeat_pid() {
    local pid="$1"
    [ -n "$pid" ] || return 0
    HEARTBEAT_PIDS="$HEARTBEAT_PIDS $pid"
}

unregister_heartbeat_pid() {
    local pid="$1"
    [ -n "$pid" ] || return 0
    local kept=""
    local p
    for p in $HEARTBEAT_PIDS; do
        if [ "$p" != "$pid" ]; then
            kept="$kept $p"
        fi
    done
    HEARTBEAT_PIDS="$kept"
}

cleanup_heartbeats() {
    local p
    for p in $HEARTBEAT_PIDS; do
        kill "$p" 2>/dev/null || true
    done
    for p in $HEARTBEAT_PIDS; do
        wait "$p" 2>/dev/null || true
    done
    HEARTBEAT_PIDS=""
}

on_exit_cleanup() {
    cleanup_heartbeats
}

trap on_exit_cleanup INT TERM EXIT

print_claude_failure_diagnostics() {
    local exit_code="$1"
    local model="$2"
    local prompt_bytes="$3"
    local stderr_file="$4"
    local stdout_file="$5"

    echo "  [🔍] -------- Claude Code failure diagnostics --------" >&2
    echo "  [🔍] exit_code=$exit_code model=$model prompt_bytes=$prompt_bytes" >&2
    echo "  [🔍] invocation: claude -p --model \"$model\"" >&2
    echo "  [🔍] cwd=$(pwd)" >&2

    local cbin
    cbin=$(command -v claude 2>/dev/null || true)
    if [ -n "$cbin" ]; then
        echo "  [🔍] claude binary: $cbin" >&2
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

    local sb sse
    sb=$(wc -c < "$stdout_file" 2>/dev/null | tr -d ' ' || echo 0)
    sse=$(wc -c < "$stderr_file" 2>/dev/null | tr -d ' ' || echo 0)
    echo "  [🔍] captured stdout_bytes=$sb stderr_bytes=$sse" >&2
    echo "  [🔍] -----------------------------------------" >&2
}

summarize_claude_stderr() {
    local f="$1"
    [ -f "$f" ] || return 0
    if grep -q 'overloaded_error\|429\|CAPACITY_EXHAUSTED' "$f" 2>/dev/null; then
        echo "  [📌] Plain summary: Anthropic API returned 429 — model is overloaded (transient)." >&2
        return 0
    fi
    if grep -q 'invalid_request_error\|400' "$f" 2>/dev/null; then
        echo "  [📌] Plain summary: Bad request (400)." >&2
        return 0
    fi
    if grep -qE '401|UNAUTHORIZED|invalid_api_key' "$f" 2>/dev/null; then
        echo "  [📌] Plain summary: Auth problem. Check ANTHROPIC_API_KEY." >&2
        return 0
    fi
}

claude_should_blacklist_model() {
    local model="$1"
    local errfile="$2"
    return 1
}

run_claude_with_fallback() {
    local PROMPT_CONTENT="$1"
    local SUCCESS=false
    local OUTPUT=""

    for MODEL in "${MODELS[@]}"; do
        if [[ " $BLACKLISTED_MODELS " =~ " $MODEL " ]]; then
            continue
        fi

        PROMPT_BYTES=${#PROMPT_CONTENT}
        echo "  [→] Calling Claude Code with model: $MODEL (prompt ~${PROMPT_BYTES} bytes)..." >&2
        echo "  [→] Started at $(date '+%Y-%m-%d %H:%M:%S %z')" >&2

        TMP_ERR=$(mktemp)
        TMP_OUT=$(mktemp)
        HEARTBEAT_TIP_DIR=$(mktemp -d)
        API_START=$(date +%s)
        (
            while true; do
                sleep 15
                NOW=$(date +%s)
                ELAPSED=$((NOW - API_START))
                echo "  [...] Still waiting for Claude Code (${ELAPSED}s elapsed, model=$MODEL)..." >&2
                if [ "$ELAPSED" -ge 300 ] && [ ! -f "$HEARTBEAT_TIP_DIR/tip300" ]; then
                    touch "$HEARTBEAT_TIP_DIR/tip300"
                    echo "  [...] Tip: 5+ minutes can be normal. Check: ps aux | grep -E '[c]laude'" >&2
                fi
            done
        ) &
        HEARTBEAT_PID=$!
        register_heartbeat_pid "$HEARTBEAT_PID"
        claude -p --model "$MODEL" --system-prompt "You are a helpful assistant with access to tools for reading and modifying files. Use the available tools to complete the task." "$PROMPT_CONTENT" >"$TMP_OUT" 2>"$TMP_ERR"
        EXIT_CODE=$?
        kill "$HEARTBEAT_PID" 2>/dev/null || true
        wait "$HEARTBEAT_PID" 2>/dev/null || true
        unregister_heartbeat_pid "$HEARTBEAT_PID"
        rm -rf "$HEARTBEAT_TIP_DIR"
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

            LAST_RUN_DIR="${TMPDIR:-/tmp}/auto_feedback_claude_last_run"
            mkdir -p "$LAST_RUN_DIR"
            cp -f "$TMP_ERR" "$LAST_RUN_DIR/stderr.txt"
            cp -f "$TMP_OUT" "$LAST_RUN_DIR/stdout.txt"
            echo "  [ℹ️] Full stdout/stderr saved to: $LAST_RUN_DIR/{stdout.txt,stderr.txt}" >&2

            if [ -s "$TMP_OUT" ]; then
                echo "  [ℹ️] claude stdout — first 40 lines:" >&2
                head -40 "$TMP_OUT" | sed 's/^/    | /' >&2
            fi

            rm -f "$TMP_ERR" "$TMP_OUT"
        fi
    done

    if [ "$SUCCESS" = false ]; then
        echo "  [❌] FATAL ERROR: All models failed. Stopping script." >&2
        rm -rf "$ORIGINAL_STATE_DIR"
        exit 1
    fi

    echo "$OUTPUT"
}

run_feedback_for_task() {
    local TASK_DIR ORIGINAL_STATE_DIR REL_PATH TASK_NAME JSON_BASE JSON_FILES
    TASK_DIR="${1%/}"
    REL_PATH=$(echo "$TASK_DIR" | sed 's|^tasks/||')
    TASK_NAME=$(basename "$REL_PATH")
    JSON_BASE="evaluation_results/${REL_PATH}/Qwen3-8B/baseline"

    echo "📦 Backing up initial state for revision tracking..."
    ORIGINAL_STATE_DIR=$(mktemp -d)
    cp -r "$TASK_DIR/"* "$ORIGINAL_STATE_DIR/"

# ==========================================
# PHASE 1: FORENSIC ANALYSIS
# ==========================================
echo "========================================================"
echo "🔬 PHASE 1: Forensic Analysis"
echo "========================================================"

# Build JSON file list for Phase 1
JSON_FILES=""
for i in 1 2 3 4; do
    JSON_PATH="${JSON_BASE}/all_Initial_to_Stage-${i}.json"
    if [ -f "$REPO_ROOT/$JSON_PATH" ]; then
        JSON_FILES="${JSON_FILES}${JSON_PATH} "
    fi
done

if [ -z "$JSON_FILES" ]; then
    echo "  [⚠️] No evaluation JSON files found at $JSON_BASE. Skipping forensic analysis."
    JSON_FILES="${JSON_BASE}/all_Initial_to_Stage-1.json ${JSON_BASE}/all_Initial_to_Stage-2.json ${JSON_BASE}/all_Initial_to_Stage-3.json ${JSON_BASE}/all_Initial_to_Stage-4.json"
fi

read -r -d '' PROMPT_PHASE_1 << EOM
# Role & Objective
You are an expert Embodied AI evaluator, physical simulation analyst, and code reviewer. I am providing you with complete JSON execution logs representing multiple iteration attempts by an LLM agent to solve a physics-based task.

The agent ultimately failed. Your objective is to conduct a meticulous forensic analysis of these JSON logs to determine the root causes of the failure.

# Warning: Data Scale
The JSON files contain very long execution records across many iterations, including code modifications, scores, physical metrics, and feedback loops. You must pay careful attention to nuances of every iteration. Do not skim.

# Core Analysis Requirements
Analyze the execution logs and provide a detailed report addressing the following 5 dimensions:

## 1. System-Level Errors & Environment Faults
* Is the task setup missing critical physical constraints, boundary conditions, or necessary environmental information?
* Are there signs that the agent was forced to "guess" parameters?
* Did the agent misuse or invent APIs?

## 2. LLM Physical Reasoning Capacity
* Is the agent demonstrating genuine multi-step physical reasoning?
* Or is it merely engaging in blind "parameter tweaking"?
* Did the agent correctly identify the root physical cause of failures?

## 3. Feedback Sparsity & Quality
* Is the feedback too sparse (e.g., only final score)?
* Does the feedback lack "process-aware" physical metrics?
* Did the lack of detailed feedback contribute to failure?

## 4. Unanticipated Failure Mechanisms
* Did the agent get trapped in a local minimum?
* Were there conflicts between physical properties the agent set?
* Did a design break the physics engine?

## 5. Trajectory of True Improvement
* Was there any true evolution in policy or solution architecture?
* Plot the trajectory of best_score and physical metrics over time.
* Did the agent actually learn from previous iterations?

# Output Format
Structure your response using clear headings for the 5 points. Cite specific iteration numbers, code snippets, and metric changes from the JSON to back up your claims.

# Input Data
Read and analyze the following JSON files:
$JSON_FILES
EOM

OUTPUT_PHASE1=$(run_claude_with_fallback "$PROMPT_PHASE_1")
echo "$OUTPUT_PHASE1"
echo "========================================================"

# ==========================================
# PHASE 2: FEEDBACK OPTIMIZATION
# ==========================================
echo "========================================================"
echo "🔧 PHASE 2: Forensic Feedback Optimization"
echo "========================================================"

read -r -d '' PROMPT_PHASE_2 << EOM
# Phase 2: Forensic Feedback Optimization
Based on the Forensic Analysis provided below, immediately proceed to refactor the \`format_task_metrics(metrics)\` function within \`${TASK_DIR}/feedback.py\`.

## Forensic Analysis (from Phase 1)
$OUTPUT_PHASE1

---

## 1. Role and Objective
You are a Senior Physics Engine Architect and Diagnostic Specialist. Your task is to refactor the \`format_task_metrics(metrics)\` function within \`${TASK_DIR}/feedback.py\`.

Your objective is to transform the current summative feedback into **High-Resolution Forensic Feedback**. Based on the **Forensic Analysis** above, identify the critical physical data that was missing or obscured and expose it through objective metrics.

## 2. Input Context: The Forensic Gap
Refer to the Forensic Analysis. Identify the "Blind Spots" — such as unknown failure timing, lack of spatial specificity, or hidden mechanical conflicts. Ensure \`format_task_metrics\` extracts and formats exactly this data from the \`metrics\` dictionary.

## 3. Ground Truth & Permitted Modifications
1. **Objective Target:** Rewrite \`format_task_metrics\` in \`feedback.py\`.
2. **Supportive Additions:** You may make **minimal, additive changes** to \`environment.py\` (adding tracking) and \`evaluator.py\` (including those tracked values in metrics).
3. **Strictly Additive:** Do NOT modify any existing underlying physics logic, backbone environmental settings, task constraints, or success criteria.
4. **No Hallucinations:** Do not report metrics that are not being tracked.

## 4. Strict Constraints
1. **No Spoilers:** \`format_task_metrics\` must remain strictly objective. Report **what happened**, **where**, **to what magnitude**. NEVER provide engineering advice.
2. **No Hardcoding:** Never use fixed environmental thresholds. Always compare against metrics dict values (e.g., \`metrics.get('max_structure_mass')\`).
3. **Function Isolation:** Do NOT modify \`get_improvement_suggestions\`.
4. **Zero-Tolerance on Environment Retuning:** Do NOT change existing numeric defaults or pass/fail semantics.

## 5. Engineering Requirements for \`format_task_metrics\`
* **Temporal/Event Resolution:** Report Timeline of Failure (e.g., "Step 45: First joint failure at x=10.2").
* **Spatial Context & Boundary Margins:** Report proximity to failure (e.g., "Elevation margin above fail-zone: 0.15m" or "Peak Stress: 98% of 80N limit").
* **Numerical Health:** Identify solver divergence or "Numerical Instability" (NaNs, Infinite velocities, extreme spikes).
* **Phase-Aware Segregation:** Divide metrics by simulation phases if the data supports it.

## 6. Verification & Validation Phase
After implementing the changes:
1. Execute mutated tests (e.g., \`test_initial_on_mutated.py\` or \`test_mutated_tasks\`) to simulate the INITIAL reference solution against the four mutated environments.
2. The ideal state: reference solution **PASSES** initial environment but **FAILS** on all mutated tasks.
3. Inspect failure logs to verify forensic data (timing, location, peak forces) is correctly populated.

## 7. Execution Steps
1. **Analyze Ground Truth:** Review \`environment.py\` and \`evaluator.py\` to see what is currently tracked.
2. **Implement Tracking:** Add necessary additive tracking variables to \`environment.py\` and pass them through \`evaluator.py\`.
3. **Rewrite \`format_task_metrics\`:** Use Python (2-3 decimal precision).
4. **Validate:** Run the tests. If feedback is still vague, refine until forensic output is high-resolution.

## 8. Output Format
1. If you modified \`environment.py\` or \`evaluator.py\`, provide those **additive** changes first.
2. Provide the complete, refactored Python code for the \`format_task_metrics\` function.
3. Summarize verification results.
4. Explain how these new metrics resolve the "Blind Spots" from the Forensic Analysis.

**CRITICAL:** After your analysis, immediately use your tools to modify the files and implement the new tracking variables and the rewritten \`format_task_metrics\` function.
EOM

OUTPUT_PHASE2=$(run_claude_with_fallback "$PROMPT_PHASE_2")
echo "$OUTPUT_PHASE2"
echo "========================================================"

# ==========================================
# PHASE 3: QA AUDIT LOOP
# ==========================================
echo "========================================================"
echo "🔍 PHASE 3: QA Audit Loop"
echo "========================================================"

ITERATION=1
while true; do
    echo "========================================================"
    echo "🔄 QA Iteration $ITERATION for $TASK_DIR..."
    echo "========================================================"

    read -r -d '' PROMPT_QA << EOM
For ${TASK_NAME}
# Strict Quality Assurance (QA) Code Auditor

## 1. Role and Objective
You are a Strict QA Code Auditor for a physics-based AI benchmark. Audit the newly generated \`feedback.py\` (specifically the \`format_task_metrics\` function) against the **GROUND TRUTH** files (\`${TASK_DIR}/environment.py\`, \`${TASK_DIR}/evaluator.py\`, \`${TASK_DIR}/prompt.py\`, and \`${TASK_DIR}/stages.py\`).

Your absolute priority is **Code-Grounded Truth**. Ensure every metric reported is physically tracked and feedback remains purely objective.

## 2. Strict Audit Checklist
Execute the following 4 audits step-by-step. If \`format_task_metrics\` fails any check, correct it.

### Audit 1: The Traceability Check (Zero Tolerance)
* **Action:** Trace every key used in \`format_task_metrics\` back to the \`metrics\` dictionary returned by \`evaluator.py\`.
* **Ground Truth Exception:** If the previous turn added new tracking variables, those specific **additive changes** are now part of your Ground Truth.
* **Rule:** If a metric is mentioned but is **NOT** explicitly tracked, **DELETE IT**.

### Audit 2: The Hardcode Purge (Dynamic Stage Check)
* **Action:** Scan for any raw numeric physical thresholds (e.g., \`> 80.0\`, \`15m gap\`).
* **Rule:** Parameters mutate across stages. Use \`.get('key', default)\`. Replace all hardcoded constants with dynamic lookups.

### Audit 3: The "No-Spoilers" Verification
* **Action:** Ensure \`format_task_metrics\` remains **purely descriptive**.
* **Rule:** If it includes phrases like "You should..." or "Consider...", or labels a failure as "due to poor bracing," rewrite to be purely numeric/spatial.

### Audit 4: The Scope Lockdown
* **Action:** Verify **ONLY** necessary parts of \`feedback.py\` (and supporting tracking) have been modified.
* **Rule:** \`get_improvement_suggestions\` and unrelated functions must remain untouched.

### Audit 5: Environment Drift Guard
* **Rule:** Any edit to pre-existing numeric defaults or pass/fail semantics is a hard failure; revert it. Only additive telemetry is allowed.

## 3. Empirical Verification Audit (Mandatory)
1. **Execute Mutated Tests:** Run appropriate test script (e.g., \`python ${TASK_DIR}/test_initial_on_mutated.py\`).
2. **Verify Baseline & Mutants:** Confirm initial reference **PASSES** base but **FAILS** on all four mutated tasks.
3. **Audit the Logs:** Verify forensic data (timing, locations, forces) is present and accurate.
4. **Confirm Dynamic Grounding:** Verify "Limits" in logs reflect specific mutation values from \`stages.py\`.

## 4. Execution Steps
1. **Static Analysis:** Compare \`format_task_metrics\` against \`evaluator.py\` return dictionary.
2. **Sanitize:** Apply Audit Checklist to remove hallucinations and hardcoded values.
3. **Environment Drift Check:** Confirm no forbidden behavior-changing edits exist.
4. **Empirical Test:** Run the tests.
5. **Final Output:**
    * **If issues were found/corrected:** Use tools to modify files and fix issues.
    * **If NO issues were found:** Do NOT modify code. State: "Audit complete: No issues found."

## 5. Final Confirmation
Does this code provide high-resolution, objective data without hallucinating or spoiling the solution? If it is already perfect, do not change it.
EOM

    OUTPUT_QA=$(run_claude_with_fallback "$PROMPT_QA")
    echo "$OUTPUT_QA"

    echo "========================================================"
    echo "🧠 Evaluating QA Response..."

    read -r -d '' CLASSIFY_PROMPT << EOM
Analyze the following QA audit report.
Did the auditor find any issues that needed correcting?
- If the auditor stated "Audit complete: No issues found" and made NO modifications, reply with exactly the word "CLEAN".
- If the auditor found ANY issues, applied fixes, or report is ambiguous, reply with exactly the word "DIRTY".
Reply with NOTHING ELSE but that single word.

Report to analyze:
$OUTPUT_QA
EOM

    CLASSIFICATION=$(run_claude_with_fallback "$CLASSIFY_PROMPT")
    CLASSIFICATION=$(echo "$CLASSIFICATION" | xargs)

    echo "Classification Result: [$CLASSIFICATION]"

    if [ "$CLASSIFICATION" = "CLEAN" ]; then
        echo "✅ QA Audit passed! Breaking loop."
        break
    else
        echo "⚠️  QA issues detected and fixed. Re-auditing..."
        ITERATION=$((ITERATION+1))
    fi
done

# ==========================================
# GENERATE LOG / DIFF
# ==========================================
echo "========================================================"
echo "📝 Generating revision patch log..."

LOG_DIR="tasks/auto_audit_log/$REL_PATH"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/revisions_feedback.patch"

diff -ruN -x "__pycache__" "$ORIGINAL_STATE_DIR" "$TASK_DIR" > "$LOG_FILE"

if [ -s "$LOG_FILE" ]; then
    echo "✅ Success: Feedback revisions saved to $LOG_FILE"
else
    echo "ℹ️ No changes were made to the files during this process."
    rm -f "$LOG_FILE"
fi

rm -rf "$ORIGINAL_STATE_DIR"

# Generate HANDOFF.md for cross-session continuity
HANDOFF_FILE="$LOG_DIR/HANDOFF.md"
cat > "$HANDOFF_FILE" << EOF
# Feedback Handoff: $(basename "$TASK_DIR")
## Timestamp: $(date '+%Y-%m-%d %H:%M:%S %z')
## Task: $TASK_DIR
## Spec: $TASK_SPEC
## Total QA Iterations: $ITERATION

## Last Run Status
$(if [ "$CLASSIFICATION" = "CLEAN" ]; then echo "Status: CLEAN - Feedback validated"; else echo "Status: DIRTY - QA iterations completed"; fi)

## Log Files
- Feedback revisions: revisions_feedback.patch
EOF

echo "📋 Handoff file generated: $HANDOFF_FILE"
echo "========================================================"
}

for TASK_DIR in "${TASK_DIRS[@]}"; do
    echo "========================================================"
    echo "▶ Auto-feedback task: $TASK_DIR  (spec: $TASK_SPEC, ${#TASK_DIRS[@]} total)"
    echo "========================================================"
    run_feedback_for_task "$TASK_DIR" || exit 1
done
