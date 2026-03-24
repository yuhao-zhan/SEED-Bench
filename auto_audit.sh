#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: ./auto_audit.sh <task_directory>"
  echo "Example: ./auto_audit.sh tasks/Category1_Statics_Equilibrium/S_01"
  exit 1
fi

# Remove trailing slash if user provided one
TASK_DIR=${1%/}

# ==========================================
# SETUP REVISION TRACKING
# ==========================================
echo "📦 Backing up initial state for revision tracking..."
ORIGINAL_STATE_DIR=$(mktemp -d)
# Copy the contents of the target directory to our temp folder
cp -r "$TASK_DIR/"* "$ORIGINAL_STATE_DIR/"

# ==========================================
# MODEL CONFIGURATION
# ==========================================
# Try `auto` first (CLI routes to an available model), then explicit fallbacks.
MODELS=("auto" "gemini-3.1-pro-preview" "gemini-3.1-flash-lite-preview" "gemini-3-flash-preview" "gemini-2.5-pro")

# Global variable to track models that have failed (quota or crash) during this run
BLACKLISTED_MODELS=""

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

    if [ "${AUTO_AUDIT_VERBOSE:-0}" = "1" ]; then
        echo "  [🔍] AUTO_AUDIT_VERBOSE=1: env names containing GEMINI/GOOGLE/PROXY (values hidden):" >&2
        env | grep -iE '^(GEMINI|GOOGLE_|HTTP_|HTTPS_|ALL_|NO_)' | while IFS= read -r line; do
            name="${line%%=*}"
            echo "  [🔍]   ${name}=<hidden>" >&2
        done || true
    fi
    echo "  [🔍] Tip: AUTO_AUDIT_VERBOSE=1 ./auto_audit.sh ... for extra env listing" >&2
    echo "  [🔍] -----------------------------------------" >&2
}

# One-line plain-English hint from stderr (so you do not have to read 1000+ lines of stack).
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

# Return 0 if we should blacklist this model after failure; 1 if we should not (auto, or transient 429).
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

# Function to run Gemini with model fallback
run_gemini_with_fallback() {
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
        if [ "$MODEL" = "auto" ]; then
            echo "  [→] Calling API with model: auto — CLI auto-selects an available model (prompt ~${PROMPT_BYTES} bytes)..." >&2
        else
            echo "  [→] Calling API with model: $MODEL (prompt ~${PROMPT_BYTES} bytes)..." >&2
        fi
        echo "  [→] Started at $(date '+%Y-%m-%d %H:%M:%S %z') — headless \`gemini -y -p\` runs the agent (tools/files); stdout is buffered until the CLI exits." >&2

        # Capture stdout and stderr separately: some CLI versions print errors on stdout.
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
                    echo "  [...] Tip: 5–30+ minutes can be normal for a big audit. Check the process: ps aux | grep -E '[g]emini'" >&2
                fi
            done
        ) &
        HEARTBEAT_PID=$!
        gemini -y --model "$MODEL" -p "$PROMPT_CONTENT" >"$TMP_OUT" 2>"$TMP_ERR"
        EXIT_CODE=$?
        kill "$HEARTBEAT_PID" 2>/dev/null || true
        wait "$HEARTBEAT_PID" 2>/dev/null || true
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

            LAST_RUN_DIR="${TMPDIR:-/tmp}/auto_audit_gemini_last_run"
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
        echo "  [❌] FATAL ERROR: All models failed or exhausted their quota. Stopping loop." >&2
        rm -rf "$ORIGINAL_STATE_DIR" # Cleanup on fail
        exit 1
    fi

    # Echo the clean output back to the caller
    echo "$OUTPUT"
}

# ==========================================
# PROMPTS
# ==========================================
read -r -d '' PROMPT << EOM
# Objective
Conduct a strict audit of the task in the following directory: '${TASK_DIR}'. Use your tools to systematically list and read all relevant code files there. Your goal is to analyze the existing code for logic, consistency, and expected failure states, reporting any violations.

## STRICT RULE 1: FIX MODE ENABLED
You are acting as an auditor AND an engineer. Your final output must consist of your analysis, a comprehensive list of violation cases, AND you MUST use your tools to modify and fix ANY and ALL violations you find.

## STRICT RULE 2: ANTI-LAZINESS & EXHAUSTIVE COMPLETENESS (CRITICAL)
You must NOT stop after finding 1 or 2 errors. Do not provide "examples" of violations; you must provide an EXHAUSTIVE, line-by-line enumeration of EVERY SINGLE violation in the entire directory. To ensure completeness, you must mentally extract a full list of every physical parameter in \`environment.py\` and trace EACH ONE through every other module. 

Please perform the following audit steps for every task in the directory:

### Step 1: Cross-Module Consistency Audit
Systematically review all modules within the task directory (including \`environment.py\`, \`evaluator.py\`, \`feedback.py\`, \`prompt.py\`, \`stages.py\`, and \`renderer.py\`).
* **Expected Outcome:** All modules must be logically consistent and coherent. The physical mechanics and parameters defined in the underlying environment (especially in mutated tasks) MUST perfectly align with the evaluation logic and the prompt descriptions.
* **Action:** Document EVERY SINGLE discrepancy, logical conflict, or misaligned physics across these files. Trace every constant.

## Step 2: Information Consistency & Visibility Audit (VISIBLE vs. INVISIBLE)
Carefully scrutinize how physical variables and constraints are handled across the modules. You must strictly adhere to the following definitions of VISIBLE and INVISIBLE information:

### 1. Constraint Completeness (Defining "VISIBLE")
* **Definition:** "VISIBLE" variables do NOT merely mean "visible to the naked eye." A variable is VISIBLE if it is explicitly mentioned in the initial task description (\`prompt.py\`). 
* **Audit Rule:** You must cross-reference \`environment.py\` and \`evaluator.py\` to ensure that **ALL necessary structural limits and boundaries** are explicitly stated in the initial prompt. This universally includes **ANY** variable that defines an absolute maximum, minimum, or failure threshold required to solve the task (e.g., maximum mass budgets, minimum target heights, force/torque limits for joints, time limits, or strict geometric boundaries). Since these are required constraints for the agent to mathematically or logically solve the task, they MUST be explicitly prompted (making them VISIBLE).
* **Exhaustive Check:** Scan \`environment.py\` for ANY hardcoded numbers or limits. If it is a structural limit needed to solve the task, verify it is in \`prompt.py\`. Document EVERY omission.

### 2. Mutation Synchronization (Updating VISIBLE Changes)
* **Audit Rule:** If \`stages.py\` modifies ANY variable that is VISIBLE (i.e., mentioned in the prompt, such as gap width, mass budget, or target coordinates), the prompt string **MUST** be dynamically updated to reflect the new value while explicitly keeping a record of the old value.
* **Format Requirement:** The prompt update logic must strictly follow the format: \`[new_value] (originally [old_value] in the source environment)\`. You can refer to \`@'tasks/Category1_Statics_Equilibrium/S_01/stages.py'\`.
* **CRITICAL - Execution Verification:** Because these dynamic updates heavily rely on complex Regular Expressions (\`regex\`) or string replacements, you MUST NOT blindly trust the code. You must actively dry-run or conceptually execute EVERY SINGLE regex logic block in \`stages.py\` to ensure it successfully captures the target string and accurately outputs the exact required format. 
* *Example Check:* If a mass budget changes from 380kg to 200kg, the prompt must output: \`200kg (originally 380kg in the source environment)\`. Document ANY regex mismatches, failures to capture, or malformed string outputs.

### 3. Hidden Physics Protection (Defining "INVISIBLE")
* **Definition:** "INVISIBLE" variables are underlying environmental physical constants that cannot be directly observed by the naked eye (e.g., gravitational acceleration, global friction coefficients, wind force, earthquake amplitude/frequency).
* **Audit Rule:** The exact values, magnitudes, or directions of change (e.g., "gravity increased to -25", "friction reduced") of these invisible constants **MUST NOT** be mentioned in the prompt under any circumstances. The agent is forced to infer these specific anomalies through physical interaction and feedback.
* **CRITICAL EXCEPTION:** Mentioning the mere *name* of the variable as a general warning is ONLY allowed within the \`UNIFORM_SUFFIX\` (see Sub-step 4 below). 
* *Action:* Check EVERY line of \`prompt.py\` and the regex outputs in \`stages.py\`. Document EVERY instance where an INVISIBLE environmental constant's specific value or explicit change direction is leaked.

### 4. The \`UNIFORM_SUFFIX\` Audit (The "Union" Rule)
* **Audit Rule:** The \`UNIFORM_SUFFIX\` (appended at the end of the prompt for mutated stages) MUST dynamically list the **UNION** of all physical variables that have been modified across Stage-1, Stage-2, Stage-3, and Stage-4 in \`stages.py\`.
* **Format & Tone Restriction:** The suffix must ONLY provide a general warning about *what* might have changed (e.g., "Gravitational acceleration: Vertical loads may be significantly different."). It MUST NEVER pinpoint the exact mutations, specific values, or directions of change for any specific stage. The ideal scenario is telling the model *what* variables might change, but never *how* they change.
* *Action:* Document EVERY instance where the \`UNIFORM_SUFFIX\` fails to include a modified variable from the union of all 4 stages, OR where it violates the tone by explicitly stating *how* a variable changes.

---
### ACTION REQUIRED based on your findings:
**Final Deliverable:** Provide an exhaustively detailed list of all violations categorized by the steps above. If a category has no violations, explicitly state "No violations found for [Category]". Do not summarize; be hyper-specific.

**CRITICAL FIXING STEP:** After listing the violations, you MUST immediately use your tools to modify the files to fix EVERY SINGLE VIOLATION you found. You are not just auditing; you are fixing the code in this same turn.
EOM

# ==========================================
# EXECUTION LOOP
# ==========================================
ITERATION=1
while true; do
    echo "========================================================"
    echo "🔄 Iteration $ITERATION: Running fresh audit on $TASK_DIR..."
    echo "========================================================"
    
    OUTPUT=$(run_gemini_with_fallback "$PROMPT")
    
    echo "$OUTPUT"
    echo "========================================================"
    echo "🧠 Evaluating LLM Response for Completion Status..."
    
    read -r -d '' CLASSIFY_PROMPT << EOM
Analyze the following report from a code auditor.
Did the auditor find ANY violations? 
- If the auditor found ZERO violations and the code is perfectly clean (e.g., stated "No violations found" for all categories), reply with exactly the word "CLEAN".
- If the auditor found ANY violations (even if they fixed them), or if the report is ambiguous, reply with exactly the word "DIRTY".
Reply with NOTHING ELSE but that single word.

Report to analyze:
$OUTPUT
EOM

    CLASSIFICATION=$(run_gemini_with_fallback "$CLASSIFY_PROMPT")
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
echo "========================================================"
