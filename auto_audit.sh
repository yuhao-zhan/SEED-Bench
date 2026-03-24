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
# Define the models to try in order of preference
MODELS=("gemini-3.1-pro-preview" "gemini-3.1-flash-lite-preview" "gemini-3-flash-preview" "gemini-2.5-pro")

# Global variable to track models that have failed (quota or crash) during this run
BLACKLISTED_MODELS=""

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

        echo "  [→] Calling API with model: $MODEL..." >&2
        
        # Redirect stderr to a temp file so we don't pollute the actual output string,
        # but we can still capture the exit code to detect crashes/quota errors.
        TMP_ERR=$(mktemp)
        OUTPUT=$(gemini -y --model "$MODEL" -p "$PROMPT_CONTENT" 2> "$TMP_ERR")
        EXIT_CODE=$?
        
        if [ $EXIT_CODE -eq 0 ]; then
            SUCCESS=true
            rm -f "$TMP_ERR"
            break
        else
            echo "  [⚠️] Model $MODEL failed. Error details:" >&2
            # Print the last few lines of the error to avoid flooding the screen
            tail -n 5 "$TMP_ERR" >&2
            echo "  [🚫] Adding $MODEL to blacklist. It will be skipped for the rest of this session." >&2
            BLACKLISTED_MODELS="$BLACKLISTED_MODELS $MODEL "
            rm -f "$TMP_ERR"
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
Conduct a strict audit of the task in the following directory: '@${TASK_DIR}'. Your goal is to analyze the existing code for logic, consistency, and expected failure states, reporting any violations.

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
