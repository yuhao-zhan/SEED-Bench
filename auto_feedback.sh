#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: ./auto_feedback.sh <task_directory>"
  echo "Example: ./auto_feedback.sh tasks/Category1_Statics_Equilibrium/S_06"
  exit 1
fi

# Remove trailing slash if user provided one
TASK_DIR=${1%/}

# Extract relative path (e.g., Category1_Statics_Equilibrium/S_06)
REL_PATH=$(echo "$TASK_DIR" | sed 's|^tasks/||')
TASK_NAME=$(basename "$REL_PATH")

# Dynamically construct the JSON paths based on the target task
JSON_BASE="evaluation_results/${REL_PATH}/Qwen3-8B/baseline"
JSON_FILES="@${JSON_BASE}/all_Initial_to_Stage-1.json @${JSON_BASE}/all_Initial_to_Stage-2.json @${JSON_BASE}/all_Initial_to_Stage-3.json @${JSON_BASE}/all_Initial_to_Stage-4.json"

# ==========================================
# SETUP REVISION TRACKING
# ==========================================
echo "📦 Backing up initial state for revision tracking..."
ORIGINAL_STATE_DIR=$(mktemp -d)
cp -r "$TASK_DIR/"* "$ORIGINAL_STATE_DIR/"

# ==========================================
# MODEL CONFIGURATION & FALLBACK
# ==========================================
MODELS=("auto" "gemini-3.1-flash-lite-preview" "gemini-3-flash-preview" "gemini-3.1-pro-preview" "gemini-2.5-pro")
BLACKLISTED_MODELS=""

# Track background heartbeat workers so traps can always clean them.
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

# When gemini exits non-zero: print why-it-failed hints (never prints secret values).
print_gemini_failure_diagnostics() {
    local exit_code="$1"
    local model="$2"
    local prompt_bytes="$3"
    local stderr_file="$4"
    local stdout_file="$5"

    echo "  [🔍] -------- Gemini failure diagnostics --------" >&2
    echo "  [🔍] exit_code=$exit_code model=$model prompt_bytes=$prompt_bytes" >&2
    echo "  [🔍] invocation: gemini -y --model \"$model\" -p \"<prompt ${prompt_bytes} bytes>\"" >&2
    echo "  [🔍] cwd=$(pwd)" >&2
    echo "  [🔍] shell: $BASH_VERSION" >&2

    local gbin
    gbin=$(command -v gemini 2>/dev/null || true)
    if [ -n "$gbin" ]; then
        echo "  [🔍] gemini binary: $gbin" >&2
        _gv=$(timeout 8 gemini -v 2>&1 | tr '\n' ' ' || true)
        echo "  [🔍] gemini -v: ${_gv:-<failed>}" >&2
    else
        echo "  [🔍] gemini binary: NOT FOUND in PATH" >&2
    fi

    echo "  [🔍] node: $(command -v node 2>/dev/null || echo missing) $(node -v 2>/dev/null || true)" >&2
    if command -v npm >/dev/null 2>&1; then
        _npkg=$(timeout 8 npm list -g @google/gemini-cli 2>&1 | head -5 | tr '\n' ' ' || true)
        echo "  [🔍] npm -g @google/gemini-cli: ${_npkg:-<n/a>}" >&2
    fi

    for var in GEMINI_API_KEY GOOGLE_API_KEY GOOGLE_GENERATIVE_AI_API_KEY GOOGLE_GENAI_API_KEY; do
        eval "v=\${$var:-}"
        if [ -n "$v" ]; then
            echo "  [🔍] $var is SET (length ${#v} chars)" >&2
        else
            echo "  [🔍] $var is UNSET" >&2
        fi
    done

    if [ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]; then
        if [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
            echo "  [🔍] GOOGLE_APPLICATION_CREDENTIALS: file exists" >&2
        else
            echo "  [🔍] GOOGLE_APPLICATION_CREDENTIALS: set but file NOT FOUND" >&2
        fi
    else
        echo "  [🔍] GOOGLE_APPLICATION_CREDENTIALS is UNSET" >&2
    fi

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

    if [ "${AUTO_FEEDBACK_VERBOSE:-0}" = "1" ] || [ "${AUTO_AUDIT_VERBOSE:-0}" = "1" ]; then
        echo "  [🔍] verbose: env names containing GEMINI/GOOGLE/PROXY (values hidden):" >&2
        env | grep -iE '^(GEMINI|GOOGLE_|HTTP_|HTTPS_|ALL_|NO_)' | while IFS= read -r line; do
            name="${line%%=*}"
            echo "  [🔍]   ${name}=<hidden>" >&2
        done || true
    fi
    echo "  [🔍] Tip: AUTO_FEEDBACK_VERBOSE=1 ./auto_feedback.sh ... (AUTO_AUDIT_VERBOSE=1 also works)" >&2
    echo "  [🔍] -----------------------------------------" >&2
}

summarize_gemini_stderr() {
    local f="$1"
    [ -f "$f" ] || return 0
    if grep -q 'MODEL_CAPACITY_EXHAUSTED\|No capacity available for model' "$f" 2>/dev/null; then
        echo "  [📌] Plain summary: Google API returned 429 — no server capacity for this model (transient). The CLI retries with backoff, so several minutes then exit 1 is normal. Wait and retry, or rely on the next model in the fallback list." >&2
        return 0
    fi
    if grep -q 'RetryableQuotaError\|RESOURCE_EXHAUSTED' "$f" 2>/dev/null; then
        echo "  [📌] Plain summary: Quota / capacity exhausted (429). Retry later or switch model." >&2
        return 0
    fi
    if grep -qE '401|UNAUTHENTICATED|invalid_grant' "$f" 2>/dev/null; then
        echo "  [📌] Plain summary: Auth problem. Try: gemini auth (or refresh login)." >&2
        return 0
    fi
}

gemini_stderr_is_transient_capacity() {
    local f="$1"
    [ -f "$f" ] || return 1
    grep -qE 'MODEL_CAPACITY_EXHAUSTED|No capacity available for model|RetryableQuotaError|RESOURCE_EXHAUSTED|"status": 429|status: 429' "$f" 2>/dev/null
}

gemini_should_blacklist_model() {
    local model="$1"
    local errfile="$2"
    if [ "$model" = "auto" ]; then
        return 1
    fi
    if gemini_stderr_is_transient_capacity "$errfile"; then
        return 1
    fi
    return 0
}

run_gemini_with_fallback() {
    local PROMPT_CONTENT="$1"
    local SUCCESS=false
    local OUTPUT=""

    for MODEL in "${MODELS[@]}"; do
        if [[ " $BLACKLISTED_MODELS " =~ " $MODEL " ]]; then
            continue
        fi

        PROMPT_BYTES=${#PROMPT_CONTENT}
        if [ "$MODEL" = "auto" ]; then
            echo "  [→] Calling API with model: auto — CLI auto-selects an available model (prompt ~${PROMPT_BYTES} bytes)..." >&2
        else
            echo "  [→] Calling API with model: $MODEL (prompt ~${PROMPT_BYTES} bytes)..." >&2
        fi
        echo "  [→] Started at $(date '+%Y-%m-%d %H:%M:%S %z') — headless \`gemini -y -p\` runs the agent (tools/files); stdout is buffered until the CLI exits." >&2

        TMP_ERR=$(mktemp)
        TMP_OUT=$(mktemp)
        HEARTBEAT_TIP_DIR=$(mktemp -d)
        API_START=$(date +%s)
        (
            while true; do
                sleep 15
                NOW=$(date +%s)
                ELAPSED=$((NOW - API_START))
                echo "  [...] Still waiting for gemini CLI (${ELAPSED}s elapsed, model=$MODEL) — no live stream; output appears when the run finishes." >&2
                if [ "$ELAPSED" -ge 120 ] && [ ! -f "$HEARTBEAT_TIP_DIR/tip120" ]; then
                    touch "$HEARTBEAT_TIP_DIR/tip120"
                    echo "  [...] Tip: Interactive chat in another terminal uses a different mode. This script only uses headless \`-p\` (no TUI, no partial transcript here)." >&2
                fi
                if [ "$ELAPSED" -ge 300 ] && [ ! -f "$HEARTBEAT_TIP_DIR/tip300" ]; then
                    touch "$HEARTBEAT_TIP_DIR/tip300"
                    echo "  [...] Tip: 5–30+ minutes can be normal for a big feedback pass. Check the process: ps aux | grep -E '[g]emini'" >&2
                fi
            done
        ) &
        HEARTBEAT_PID=$!
        register_heartbeat_pid "$HEARTBEAT_PID"
        gemini -y --model "$MODEL" -p "$PROMPT_CONTENT" >"$TMP_OUT" 2>"$TMP_ERR"
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
            summarize_gemini_stderr "$TMP_ERR"
            print_gemini_failure_diagnostics "$EXIT_CODE" "$MODEL" "$PROMPT_BYTES" "$TMP_ERR" "$TMP_OUT"

            LAST_RUN_DIR="${TMPDIR:-/tmp}/auto_feedback_gemini_last_run"
            mkdir -p "$LAST_RUN_DIR"
            cp -f "$TMP_ERR" "$LAST_RUN_DIR/stderr.txt"
            cp -f "$TMP_OUT" "$LAST_RUN_DIR/stdout.txt"
            echo "  [ℹ️] Full stdout/stderr saved to: $LAST_RUN_DIR/{stdout.txt,stderr.txt}" >&2

            if [ -s "$TMP_OUT" ]; then
                echo "  [ℹ️] gemini stdout (errors sometimes appear here) — first 60 lines:" >&2
                OUT_LINES=$(wc -l < "$TMP_OUT")
                if [ "$OUT_LINES" -le 60 ]; then
                    sed 's/^/    | /' "$TMP_OUT" >&2
                else
                    sed -n '1,35p' "$TMP_OUT" | sed 's/^/    | /' >&2
                    echo "    | ... ($OUT_LINES lines total, truncated) ..." >&2
                    tail -n 25 "$TMP_OUT" | sed 's/^/    | /' >&2
                fi
            else
                echo "  [ℹ️] gemini stdout: (empty)" >&2
            fi

            echo "  [ℹ️] gemini stderr — full stream (often includes stack / API body):" >&2
            echo "  [ℹ️] If you see '[object Object]', the Gemini CLI bug hides details; rely on diagnostics above + files on disk." >&2
            ERR_LINES=$(wc -l < "$TMP_ERR")
            if [ "$ERR_LINES" -le 120 ]; then
                sed 's/^/    | /' "$TMP_ERR" >&2
            else
                echo "    | --- stderr (first 60 lines of $ERR_LINES) ---" >&2
                sed -n '1,60p' "$TMP_ERR" | sed 's/^/    | /' >&2
                echo "    | --- stderr (last 60 lines) ---" >&2
                tail -n 60 "$TMP_ERR" | sed 's/^/    | /' >&2
            fi

            if gemini_should_blacklist_model "$MODEL" "$TMP_ERR"; then
                echo "  [🚫] Adding $MODEL to blacklist (skipped for the rest of this script run)." >&2
                BLACKLISTED_MODELS="$BLACKLISTED_MODELS $MODEL "
            else
                echo "  [ℹ️] Not blacklisting $MODEL — auto routing or transient capacity (429); explicit models still apply on next try." >&2
            fi
            rm -f "$TMP_ERR" "$TMP_OUT"
        fi
    done

    if [ "$SUCCESS" = false ]; then
        echo "  [❌] FATAL ERROR: All models failed or exhausted their quota. Stopping script." >&2
        rm -rf "$ORIGINAL_STATE_DIR"
        exit 1
    fi

    echo "$OUTPUT"
}

# ==========================================
# PROMPT DEFINITIONS
# ==========================================

# We combine Step 1 and Step 2 into a single prompt. In a stateless API environment, 
# providing the analysis instructions and the execution instructions in one unified 
# context block guarantees the LLM bases its code changes directly on its own analysis.
read -r -d '' PROMPT_PHASE_1_2 << EOM
# PHASE 1: Forensic Analysis

## Role & Objective
You are an expert Embodied AI evaluator, physical simulation analyst, and code reviewer. I am providing you with a complete JSON execution log representing a 20-iteration attempt by an LLM agent to solve a physics-based structural engineering task (involving seismic/wind stability, structural integrity, and center of mass management). 

The agent ultimately failed. Your objective is to conduct a meticulous, forensic analysis of this extensive JSON log to determine the root causes of the failure. 

## Warning: Data Scale
The attached JSON contains a very long execution record across 20 iterations, including code modifications, scores, physical metrics, and feedback loops. You must pay careful attention to the nuances of every iteration, tracking how the code and metrics evolve (or fail to evolve) over time. Do not skim.

## Core Analysis Requirements
Please analyze the execution log and provide a detailed report addressing the following 5 dimensions:

### 1. System-Level Errors & Environment Faults
Analyze if the task setup itself sabotaged the agent. 
* Is the original task prompt (if visible/inferred) missing critical physical constraints, boundary conditions, or necessary environmental information? 
* Are there signs that the agent was forced to "guess" parameters because they weren't explicitly provided? 
* Did the agent misuse or invent APIs, suggesting the provided API documentation was unclear or incomplete?

### 2. LLM Physical Reasoning Capacity
Evaluate the agent's intrinsic problem-solving approach.
* Is the agent demonstrating genuine multi-step physical reasoning (e.g., properly utilizing mass distribution, calculating torque, applying structural engineering principles)? 
* Or is it merely engaging in blind "parameter tweaking" (e.g., randomly changing \`base_w\`, \`density\`, or \`stiffness\` without a coherent physical strategy)? 
* Did the agent correctly identify the root physical cause of its failures based on the environment?

### 3. Feedback Sparsity & Quality
Examine the feedback loop provided to the agent after each iteration.
* Is the feedback too sparse? (e.g., Does it only provide a final score and binary pass/fail status?)
* Does the feedback lack "process-aware" physical metrics that the agent needs to improve (e.g., failing to inform the agent *which* joint broke, *when* the structure collapsed, or *what* specific force caused the failure)?
* Did the lack of detailed feedback directly contribute to the agent's inability to correct its mistakes?

### 4. Unanticipated Failure Mechanisms
Identify any other obscure or underlying reasons for failure.
* Did the agent get trapped in a local minimum, unable to abandon a fundamentally flawed core design?
* Were there conflicts between the physical properties the agent set (e.g., making a structure so dense it collapsed under its own weight before the external forces even applied)?

### 5. Trajectory of True Improvement
Trace the agent's progress from Iteration 0 to Iteration 20.
* Was there any *true* evolution in the policy or solution architecture, or did the code remain structurally identical with only minor variable adjustments?
* Plot the trajectory of the \`best_score\` and physical metrics over time. Did the agent actually learn from previous iterations, or did performance fluctuate randomly?

## Output Format
Please structure your response using clear headings corresponding to the 5 points above. Cite specific iteration numbers, code snippets, and metric changes from the JSON to back up your claims.

## Input Data
${JSON_FILES}

---

# PHASE 2: Forensic Feedback Optimization
Based on your Forensic Analysis above, immediately proceed to Phase 2 in this same turn.

## 1. Role and Objective
You are a **Senior Physics Engine Architect and Diagnostic Specialist**. Your task is to refactor the \`format_task_metrics(metrics)\` function within \`@${TASK_DIR}/feedback.py\`.

Your objective is to transform the current summative feedback into **High-Resolution Forensic Feedback**. Based on the **Forensic Analysis** you just provided, you must identify the critical physical data that was missing or obscured and expose it through objective metrics so the agent can self-diagnose its failure.

## 2. Input Context: The Forensic Gap
Refer to the **Forensic Analysis** just provided. Identify the "Blind Spots" mentioned—such as unknown failure timing, lack of spatial specificity, or hidden mechanical conflicts. Your goal is to ensure \`format_task_metrics\` extracts and formats exactly this data from the \`metrics\` dictionary.

## 3. Ground Truth & Permitted Modifications
1.  **Objective Target:** Your primary cus is rewriting \`format_task_metrics\` in \`feedback.py\`.
2.  **Supportive Additions:** To provide high-resolution feedback, you may find that the \`metrics\` dictionary does not yet contain the necessary data. You are **PERMITTED** to make **minimal, additive changes** to \`environment.py\` (e.g., adding a list to track joint break events or peak stress) and \`evaluator.py\` (e.g., including those tracked values in the returned \`metrics\` dict).
3.  **Strictly Additive:** You must **NOT** modify any existing underlying physics logic, backbone environmental settings, task constraints, or success criteria. You are only adding variables for tracking and reporting.
4.  **No Hallucinations:** Do not report metrics in \`feedback.py\` that you have not explicitly ensured are being tracked and returned by the \`environment\` and \`evaluator\`.

## 4. Strict Constraints
1.  **No Spoilers:** \`format_task_metrics\` must remain strictly objective. It should report **what happened**, **where**, and **to what magnitude**. It must **NEVER** provide engineering advice (e.g., "use pivot joints").
2.  **No Hardcoding:** Never use fixed environmental thresholds (e.g., \`if mass > 2000\`). Always compare current values against limit values provided in the \`metrics\` dict (e.g., \`metrics.get('max_structure_mass')\`).
3.  **Function Isolation:** Do **NOT** modify \`get_improvement_suggestions\`. We are only optimizing the objective data stream.

## 5. Engineering Requirements for \`format_task_metrics\`
Deepen the physical output by focusing on:
*   **Temporal/Event Resolution:** Report the **Timeline of Failure** (e.g., "Step 45: First joint failure at x=10.2").
*   **Spatial Context & Boundary Margins:** Report proximity to failure (e.g., "Elevation margin above fail-zone: 0.15m" or "Peak Stress: 98% of 80N limit").
*   **Numerical Health:** Identify solver divergence or "Numerical Instability" (NaNs, Infinite velocities, or extreme spikes) to flag when a design breaks the physics engine.
*   **Phase-Aware Segregation:** Divide metrics by simulation phases (e.g., Static Load, Impact/Entry, Traversal) if the data supports it.

## 6. Verification & Validation Phase
After implementing the changes, you must verify the feedback by running the task's mutated tests:
1.  **Execute Tests:** Identify and run the appropriate test script (e.g., \`test_initial_on_mutated.py\`, \`test_mutated_tasks\`, though the exact filename may vary) to simulate the INITIAL reference solution against the four mutated environments (stage-1 to stage-4).
2.  **Observe Failure States:** The ideal validation state is that the reference solution **PASSES** the initial environment but **FAILS** on all mutated tasks (Stage-1 through Stage-4).
3.  **Inspect Metric Integrity:** Review the output logs of these failures. Verify that your new \`format_task_metrics\` logic correctly populates the forensic data (timing, location, peak forces) in the text feedback. 
4.  **Check Requirements:** Ensure the failure logs actually illuminate the "Blind Spots" identified in the Forensic Analysis.

## 7. Execution Steps
1.  **Analyze Ground Truth:** Review \`environment.py\` and \`evaluator.py\` to see what is currently tracked.
2.  **Implement Tracking:** Add necessary additive tracking variables to \`environment.py\` and pass them through \`evaluator.py\`.
3.  **Rewrite \`format_task_metrics\`:** Implement the function in \`feedback.py\` using Python (2-3 decimal precision).
4.  **Validate:** Run the tests as described in Section 6. If the feedback in the failure logs is still vague or missing the new metrics, refine the code until the forensic output is high-resolution.

## 8. Output Format
1.  If you modified \`environment.py\` or \`evaluator.py\`, provide those **additive** changes first.
2.  Provide the complete, refactored Python code for the \`format_task_metrics\` function.
3.  Briefly summarize the results of your **Verification & Validation** (e.g., "Confirmed Stage-1 failure shows torque limit exceedance at step 42").
4.  Explain how these new metrics resolve the "Blind Spots" from the Forensic Analysis.

**CRITICAL FIXING STEP:** After your analysis, you MUST immediately use your tools to modify the files and implement the new tracking variables and the rewritten \`format_task_metrics\` function.
EOM

read -r -d '' PROMPT_QA << EOM
For ${TASK_NAME}
# Strict Quality Assurance (QA) Code Auditor

## 1. Role and Objective
You are a **Strict QA Code Auditor** for a physics-based AI benchmark. Your objective is to rigidly audit the newly generated \`feedback.py\` (specifically the \`format_task_metrics\` function) against the **GROUND TRUTH** files (\`@${TASK_DIR}/environment.py\`, \`@${TASK_DIR}/evaluator.py\`, \`@${TASK_DIR}/prompt.py\`, and \`@${TASK_DIR}/stages.py\`).

Your absolute priority is **Code-Grounded Truth**. You must ensure that every metric reported is physically tracked and that the feedback remains purely objective and stage-adaptive. You must ruthlessly prune any hallucinations or "suggestion-creep" within the metrics formatting.

## 2. Strict Audit Checklist
Execute the following 4 audits step-by-step. If \`format_task_metrics\` fails any check, you must correct it. **If no issues are found across all audits, you must leave the code unchanged.**

### Audit 1: The Traceability Check (Zero Tolerance)
*   **Action:** Trace every key used in \`format_task_metrics\` back to the \`metrics\` dictionary returned by \`evaluator.py\`.
*   **Ground Truth Exception:** If the previous turn added new tracking variables to \`environment.py\` and \`evaluator.py\`, those specific **additive changes** are now part of your Ground Truth.
*   **Rule:** If a metric is mentioned but is **NOT** explicitly tracked in the \`environment\` or returned by the \`evaluator\`, **DELETE IT**.

### Audit 2: The Hardcode Purge (Dynamic Stage Check)
*   **Action:** Scan for any raw numeric physical thresholds (e.g., \`> 80.0\`, \`15m gap\`, \`max_force = 100\`).
*   **Rule:** Parameters mutate across stages (\`stages.py\`). You must force the code to read these limits from the \`metrics\` dictionary using \`.get('key', default)\`. Replace all hardcoded physical constants with dynamic lookups.

### Audit 3: The "No-Spoilers" Verification
*   **Action:** Ensure \`format_task_metrics\` remains **purely descriptive**.
*   **Rule:** If the metrics formatting includes phrases like "You should..." or "Consider...", or if it labels a failure as "due to poor bracing," it has crossed into "Suggestion" territory. **REWRITE** to be purely numeric/spatial (e.g., "Peak Stress: 120% of limit").

### Audit 4: The Scope Lockdown
*   **Action:** Verify that **ONLY** the necessary parts of \`feedback.py\` (and the supporting tracking in \`environment\`/\`evaluator\`) have been modified.
*   **Rule:** \`get_improvement_suggestions\` and unrelated functions must remain untouched. If any changes were made outside of the scope of high-resolution objective metrics, **REVERT THEM**.

## 3. Empirical Verification Audit (Mandatory)
Before finalizing the audit, you must empirically verify the feedback's behavior:
1.  **Execute Mutated Tests:** Identify and run the appropriate test script (e.g., \`python @${TASK_DIR}/test_initial_on_mutated.py\` or similar).
2.  **Verify Baseline & Mutants:** Confirm that the initial reference solution **PASSES** the base environment but **FAILS** on all four mutated tasks (Stage-1 through Stage-4).
3.  **Audit the Logs:** Inspect the failure logs. Verify that the forensic data (timing, locations, forces) generated by your \`format_task_metrics\` code is actually present and accurate.
4.  **Confirm Dynamic Grounding:** Verify that the "Limits" reported in the failure logs (e.g., max mass or joint strength) correctly reflect the specific mutation values from \`stages.py\` rather than static defaults.

## 4. Execution Steps
1.  **Static Analysis:** Compare \`format_task_metrics\` against the \`evaluator.py\` return dictionary.
2.  **Sanitize:** Apply the Audit Checklist to remove hallucinations and hardcoded values.
3.  **Empirical Test:** Run the tests as described in Section 3 to see the feedback in action.
4.  **Final Output:**
    *   **If issues were found/corrected:** Immediately use your tools to modify the files and fix the issues. Provide the complete, fully audited, and purified code. Briefly summarize the verification result.
    *   **If NO issues were found:** Do **NOT** modify the code. Simply state: "Audit complete: No issues found. Verified against simulation logs (Reference passes base, fails mutants with accurate forensic data). No modifications required."

## 5. Final Confirmation
Does this code provide high-resolution, objective data without hallucinating or spoiling the solution? If it is already perfect, do not change it.
EOM

# ==========================================
# EXECUTION WORKFLOW
# ==========================================
echo "========================================================"
echo "🚀 PHASE 1 & 2: Forensic Analysis & Feedback Optimization"
echo "========================================================"
echo "Analyzing JSON logs and applying initial feedback updates..."
OUTPUT=$(run_gemini_with_fallback "$PROMPT_PHASE_1_2")
echo "$OUTPUT"

echo "========================================================"
echo "🔍 PHASE 3: Entering QA Audit Loop..."
echo "========================================================"

ITERATION=1
while true; do
    echo "========================================================"
    echo "🔄 QA Iteration $ITERATION for $TASK_DIR..."
    echo "========================================================"
    
    OUTPUT=$(run_gemini_with_fallback "$PROMPT_QA")
    echo "$OUTPUT"
    
    echo "========================================================"
    echo "🧠 Evaluating QA Response..."
    
    read -r -d '' CLASSIFY_PROMPT << EOM
Analyze the following QA audit report.
Did the auditor find any issues that needed correcting?
- If the auditor stated "Audit complete: No issues found" (or similar phrasing indicating no changes) and made NO modifications to the code, reply with exactly the word "CLEAN".
- If the auditor found ANY issues, applied any fixes, or the report is ambiguous, reply with exactly the word "DIRTY".
Reply with NOTHING ELSE but that single word.

Report to analyze:
$OUTPUT
EOM

    CLASSIFICATION=$(run_gemini_with_fallback "$CLASSIFY_PROMPT")
    CLASSIFICATION=$(echo "$CLASSIFICATION" | xargs)
    
    echo "Classification Result: [$CLASSIFICATION]"
    
    if [ "$CLASSIFICATION" = "CLEAN" ]; then
        echo "✅ QA Audit passed! Breaking loop."
        break
    else
        echo "⚠️  QA issues detected and fixed. Wiping context and re-auditing..."
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
echo "========================================================"