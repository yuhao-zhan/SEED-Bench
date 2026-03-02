#!/bin/bash
# =============================================================================
# AZR-style 2D training launch scripts
# Run from: DaVinciBench/2D_exploration/scripts/
#
# Hyperparams match AZR repo (arXiv:2505.03335):
#   lr=1e-6, clip=0.2, temp=1.0, grad_clip=1.0, gamma=1.0 (implicit)
#   gradient_checkpointing, bf16, save_every=10
# =============================================================================
# To see the real Python traceback when a worker fails (OOM, etc.), run with:
#   TORCH_DISTRIBUTED_DEBUG=DETAIL bash ... run_train.sh ...
set -x

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
TRAIN_PY="$SCRIPT_DIR/train.py"

cd "$SCRIPTS_ROOT" || exit 1

# --- GPU selection (skip occupied GPUs) ---
# Set CUDA_VISIBLE_DEVICES to one or more comma-separated IDs. Multi-GPU = model sharded across GPUs (ZeRO-2).
# Example: CUDA_VISIBLE_DEVICES=5 $0 8b all 200  (single GPU)
# Example: CUDA_VISIBLE_DEVICES=4,5,6,7 $0 14b all 2 2  (14B: 4 GPUs recommended; 2 GPUs may OOM in generation)
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1,2,3,4,5,6,7}"
echo "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"
# Count visible GPUs so batch size is divisible by num_gpus
NUM_GPUS=$(echo "${CUDA_VISIBLE_DEVICES}" | tr ',' '\n' | wc -l)
PER_GPU_BS=8
echo "Visible GPUs: $NUM_GPUS"

# --- Choose model size ---
MODEL_SIZE="${1:-8b}"   # 8b, 14b, or 32b
TASK="${2:-all}"        # all, category_1, etc.
STEPS="${3:-200}"
# Optional 4th arg: total batch size (must be divisible by NUM_GPUS); else auto = NUM_GPUS * PER_GPU_BS
USER_TOTAL_BS="${4:-}"

case "$MODEL_SIZE" in
  8b)
    MODEL_NAME="Qwen/Qwen3-8B"
    TOTAL_BS_DEFAULT=$((NUM_GPUS * PER_GPU_BS))
    TOTAL_BS="${USER_TOTAL_BS:-$TOTAL_BS_DEFAULT}"
    MICRO_BS=1
    CONFIG="$SCRIPT_DIR/accelerate_zero2.yaml"
    MAX_RESP_LEN=8096
    ;;
  14b)
    MODEL_NAME="Qwen/Qwen3-14B"
    TOTAL_BS_DEFAULT=$((NUM_GPUS * PER_GPU_BS))
    TOTAL_BS="${USER_TOTAL_BS:-$TOTAL_BS_DEFAULT}"
    MICRO_BS=1
    CONFIG="$SCRIPT_DIR/accelerate_zero2.yaml"
    MAX_RESP_LEN=8096
    ;;
  32b)
    MODEL_NAME="Qwen/Qwen3-32B"
    TOTAL_BS_DEFAULT=$((NUM_GPUS * 4))
    TOTAL_BS="${USER_TOTAL_BS:-$TOTAL_BS_DEFAULT}"
    MICRO_BS=1
    CONFIG="$SCRIPT_DIR/accelerate_zero3.yaml"
    MAX_RESP_LEN=8096
    ;;
  *)
    echo "Usage: $0 [8b|14b|32b] [task_spec] [steps] [total_batch_size]"
    echo "  CUDA_VISIBLE_DEVICES: comma-separated GPU ids. 14B requires 4 GPUs (e.g. 4,5,6,7)."
    echo "  Single-GPU (8b only): uses optimizer CPU offload (AZ_OFFLOAD=0 to disable)."
    exit 1
    ;;
esac
# Ensure total batch is divisible by num GPUs
if [ $((TOTAL_BS % NUM_GPUS)) -ne 0 ]; then
  TOTAL_BS=$(( (TOTAL_BS / NUM_GPUS) * NUM_GPUS ))
  [ "$TOTAL_BS" -lt 1 ] && TOTAL_BS=$NUM_GPUS
fi

# Qwen3-14B: 2–3 GPUs OOM (generation all-gather or optimizer.step); optimizer CPU offload OOMs system RAM (SIGKILL). Require 4 GPUs.
if [ "$MODEL_SIZE" = "14b" ] && [ "$NUM_GPUS" -lt 4 ]; then
  echo "ERROR: Qwen3-14B requires exactly 4 GPUs (2–3 GPUs OOM on GPU or CPU). Use: CUDA_VISIBLE_DEVICES=4,5,6,7 bash $0 14b all 2 1"
  exit 1
fi

# Single-GPU: use optimizer CPU offload (avoids OOM at optimizer.step() on 79GB with 8B)
# Set AZ_OFFLOAD=0 to force no offload (may OOM).
if [ "$NUM_GPUS" -eq 1 ] && [ "${AZ_OFFLOAD:-1}" = "1" ]; then
  if [ "$MODEL_SIZE" = "8b" ] || [ "$MODEL_SIZE" = "14b" ]; then
    CONFIG="$SCRIPT_DIR/accelerate_zero2_offload.yaml"
    export ACCELERATE_DEEPSPEED_OFFLOAD_OPTIMIZER_DEVICE=cpu
    echo "Single-GPU: using low-memory config (optimizer on CPU): $CONFIG"
  fi
fi

# 14B: only 4+ GPUs (script exits above if <4). ZeRO-3 no-offload, max_response_length=2048.
if [ "$MODEL_SIZE" = "14b" ] && [ "$NUM_GPUS" -ge 4 ]; then
  CONFIG="$SCRIPT_DIR/accelerate_zero3_no_offload.yaml"
  [ -z "${MAX_RESP_LEN_OVERRIDE:-}" ] && MAX_RESP_LEN=2048
  echo "14B (4 GPUs): ZeRO-3 no-offload, max_response_length=${MAX_RESP_LEN}: $CONFIG"
fi

# Logs go under absoulute_zero/runs/{model}_{task}_{date}/
# train.py auto-creates descriptive subdirectory when using the default runs/ path
AZ_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="${AZ_DIR}/runs"

echo "========================================"
echo "Model:      $MODEL_NAME"
echo "Config:     $CONFIG"
echo "Task:       $TASK"
echo "Steps:      $STEPS"
echo "Batch:      $TOTAL_BS (micro=$MICRO_BS)"
echo "Log dir:    $LOG_DIR"
echo "========================================"

accelerate launch \
  --config_file "$CONFIG" \
  --num_processes "$NUM_GPUS" \
  "$TRAIN_PY" \
  --model-name "$MODEL_NAME" \
  --task "$TASK" \
  --total-batch-size "$TOTAL_BS" \
  --micro-batch-size "$MICRO_BS" \
  --steps "$STEPS" \
  --lr 1e-6 \
  --clip-ratio 0.2 \
  --grad-clip 1.0 \
  --temperature 1.0 \
  --top-p 1.0 \
  --max-prompt-length 8096 \
  --max-response-length "${MAX_RESP_LEN:-8096}" \
  --max-steps-verifier 10000 \
  --log-dir "$LOG_DIR" \
  --save-every 10 \
  --seed 42
