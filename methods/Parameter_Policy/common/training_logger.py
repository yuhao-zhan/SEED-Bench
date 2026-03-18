"""
Unified training logger for Parameter_Policy methods.

Saves under log_dir:
  - training_config.json   : run config (method params, benchmark params, official-alignment checklist)
  - training_loss.jsonl    : one line per step/epoch with step, loss, and optional extra
  - training_loss.json     : full array for plotting (loss-step curve)
  - training_warnings.jsonl: warnings and errors during training
  - training_summary.txt   : human-readable summary + checklist for debug
  - rollouts/              : all LLM outputs during rollout (when enabled)
      - llm_calls.jsonl    : every LLM call in order (full prompt + raw_output + code + score/feedback)
      - episodes/          : (RAGEN) one JSON per episode
      - epochs/            : (Discover) one JSON per epoch
      - generations/       : (SOAR) one JSON per generation
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


class TrainingLogger:
    def __init__(
        self,
        log_dir: str,
        method_name: str,
        task_name: str = "",
        max_iterations: Optional[int] = None,
        max_steps_verifier: Optional[int] = None,
    ):
        self.log_dir = os.path.abspath(log_dir)
        self.method_name = method_name
        self.task_name = task_name
        self.max_iterations = max_iterations
        self.max_steps_verifier = max_steps_verifier
        self._config = {
            "method": method_name,
            "task_name": task_name,
            "max_iterations": max_iterations,
            "max_steps_verifier": max_steps_verifier,
            "started_at": datetime.now().isoformat(),
            "benchmark_checklist": {},
            "method_params": {},
        }
        self._loss_steps = []
        self._warnings = []
        self._errors = []
        self._finalized = False
        self._rollout_seq = 0
        self._rollouts_dir = os.path.join(self.log_dir, "rollouts")
        os.makedirs(self.log_dir, exist_ok=True)

    def log_config(
        self,
        prompt_format: str = "format_initial_prompt / format_revision_prompt_best_plus_previous",
        max_iterations_used: Optional[int] = None,
        **method_params,
    ):
        self._config["prompt_format"] = prompt_format
        if max_iterations_used is not None:
            self._config["max_iterations_used"] = max_iterations_used
        self._config["benchmark_checklist"] = {
            "max_iterations_used": self.max_iterations is not None
            and (max_iterations_used is None or max_iterations_used == self.max_iterations),
            "prompt_format": "evaluation.prompt (format_initial_prompt, format_revision_*)",
            "verifier_max_steps": self.max_steps_verifier,
        }
        self._config["method_params"].update(method_params)
        path = os.path.join(self.log_dir, "training_config.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def log_loss_step(self, step: int, loss: float, **extra):
        row = {"step": step, "loss": loss, **extra}
        self._loss_steps.append(row)
        path = os.path.join(self.log_dir, "training_loss.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def log_warning(self, message: str, **extra):
        row = {"ts": datetime.now().isoformat(), "level": "warning", "message": message, **extra}
        self._warnings.append(row)
        path = os.path.join(self.log_dir, "training_warnings.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def log_error(self, message: str, **extra):
        row = {"ts": datetime.now().isoformat(), "level": "error", "message": message, **extra}
        self._errors.append(row)
        path = os.path.join(self.log_dir, "training_warnings.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def log_prompt_sample(self, prompt_type: str, content: str, truncate: int = 2000):
        sample = content[:truncate] + ("..." if len(content) > truncate else "")
        path = os.path.join(self.log_dir, "prompt_sample.txt")
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n--- " + prompt_type + " ---\n" + sample + "\n")

    # -------------------------------------------------------------------------
    # Rollout logging: save every LLM call (prompt + raw_output + code + result)
    # -------------------------------------------------------------------------
    def log_rollout_llm_call(
        self,
        prompt_text: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        raw_output: Optional[str] = None,
        extracted_code: Optional[str] = None,
        score: Optional[float] = None,
        success: Optional[bool] = None,
        error: Optional[str] = None,
        feedback: Optional[str] = None,
        token_usage: Optional[Dict[str, Any]] = None,
        episode: Optional[int] = None,
        turn: Optional[int] = None,
        epoch: Optional[int] = None,
        generation: Optional[int] = None,
        iteration: Optional[int] = None,
        candidate_idx: Optional[int] = None,
        **extra,
    ):
        """Append one LLM call (one generate + verify) to rollouts/llm_calls.jsonl."""
        self._rollout_seq += 1
        row = {
            "seq": self._rollout_seq,
            "ts": datetime.now().isoformat(),
            "episode": episode,
            "turn": turn,
            "epoch": epoch,
            "generation": generation,
            "iteration": iteration,
            "candidate_idx": candidate_idx,
            "prompt_text": prompt_text,
            "messages": messages,
            "raw_output": raw_output,
            "extracted_code": extracted_code,
            "score": score,
            "success": success,
            "error": error,
            "feedback": feedback,
            "token_usage": token_usage,
            **extra,
        }
        os.makedirs(self._rollouts_dir, exist_ok=True)
        path = os.path.join(self._rollouts_dir, "llm_calls.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def log_rollout_episode(self, episode_idx: int, episode_dict: Dict[str, Any]):
        """Save full episode (RAGEN: all turns) to rollouts/episodes/episode_{idx:03d}.json."""
        os.makedirs(os.path.join(self._rollouts_dir, "episodes"), exist_ok=True)
        path = os.path.join(self._rollouts_dir, "episodes", f"episode_{episode_idx:03d}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(episode_dict, f, indent=2, ensure_ascii=False)

    def log_rollout_epoch(self, epoch_idx: int, trajectories: List[Dict[str, Any]]):
        """Save all trajectories of one epoch (Discover) to rollouts/epochs/epoch_{idx:03d}.json."""
        os.makedirs(os.path.join(self._rollouts_dir, "epochs"), exist_ok=True)
        path = os.path.join(self._rollouts_dir, "epochs", f"epoch_{epoch_idx:03d}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"epoch": epoch_idx, "trajectories": trajectories}, f, indent=2, ensure_ascii=False)

    def log_rollout_generation(self, gen_idx: int, steps: List[Dict[str, Any]]):
        """Save one generation's steps (SOAR: iterations + best per step) to rollouts/generations/gen_{idx:03d}.json."""
        os.makedirs(os.path.join(self._rollouts_dir, "generations"), exist_ok=True)
        path = os.path.join(self._rollouts_dir, "generations", f"gen_{gen_idx:03d}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"generation": gen_idx, "steps": steps}, f, indent=2, ensure_ascii=False)

    def finalize(self, summary_extra: Optional[Dict[str, Any]] = None):
        if self._finalized:
            return
        self._finalized = True
        self._config["finished_at"] = datetime.now().isoformat()
        if summary_extra:
            self._config["summary"] = summary_extra

        if self._loss_steps:
            path = os.path.join(self.log_dir, "training_loss.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._loss_steps, f, indent=2, ensure_ascii=False)
            self._plot_loss_curve()

        lines = [
            "Method: " + self.method_name,
            "Task: " + self.task_name,
            "Max iterations (benchmark): " + str(self.max_iterations),
            "Started: " + str(self._config.get("started_at")),
            "Finished: " + str(self._config.get("finished_at")),
            "",
            "Benchmark checklist:",
            "  max_iterations_used: " + str(self._config.get("benchmark_checklist", {}).get("max_iterations_used", "N/A")),
            "  prompt_format: " + str(self._config.get("benchmark_checklist", {}).get("prompt_format", "N/A")),
            "  verifier_max_steps: " + str(self.max_steps_verifier),
            "",
            "Loss steps recorded: " + str(len(self._loss_steps)),
            "Warnings: " + str(len(self._warnings)),
            "Errors: " + str(len(self._errors)),
        ]
        if summary_extra:
            lines.append("")
            lines.append("Summary extra:")
            for k, v in summary_extra.items():
                lines.append("  " + str(k) + ": " + str(v))
        if self._warnings:
            lines.append("")
            lines.append("Warnings:")
            for w in self._warnings[-20:]:
                lines.append("  [" + str(w.get("ts")) + "] " + str(w.get("message")))
        if self._errors:
            lines.append("")
            lines.append("Errors:")
            for e in self._errors:
                lines.append("  [" + str(e.get("ts")) + "] " + str(e.get("message")))

        path = os.path.join(self.log_dir, "training_summary.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        config_path = os.path.join(self.log_dir, "training_config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def _plot_loss_curve(self):
        """Plot loss vs step and save as loss_vs_step.png in log_dir."""
        if not self._loss_steps:
            return
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return
        steps = [s.get("step") for s in self._loss_steps]
        losses = [s.get("loss") for s in self._loss_steps]
        if not steps or not losses:
            return
        fig, ax = plt.subplots()
        ax.plot(steps, losses, marker="o", markersize=2, linestyle="-", linewidth=1)
        ax.set_xlabel("Step")
        ax.set_ylabel("Loss")
        ax.set_title(f"{self.method_name} training loss")
        fig.tight_layout()
        loss_fig_dir = os.path.join(self.log_dir, "loss_fig")
        os.makedirs(loss_fig_dir, exist_ok=True)
        out_path = os.path.join(loss_fig_dir, "loss_vs_step.png")
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        return out_path

    def get_log_dir(self):
        return self.log_dir
