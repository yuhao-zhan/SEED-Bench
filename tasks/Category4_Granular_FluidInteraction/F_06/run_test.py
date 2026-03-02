#!/usr/bin/env python3
"""Run F_06 verification with local agent.py and save GIF on success."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier


def main():
    task_name = "Category4_Granular_FluidInteraction/F_06"
    agent_path = os.path.join(os.path.dirname(__file__), "agent.py")
    with open(agent_path, "r", encoding="utf-8") as f:
        code = f.read()

    gif_path = os.path.join(os.path.dirname(__file__), "reference_solution_success.gif")
    verifier = CodeVerifier(task_name=task_name, max_steps=10000)
    success, score, metrics, error = verifier.verify_code(
        code=code,
        headless=True,
        save_gif_path=gif_path,
    )

    print("Success:", success)
    print("Score:", score)
    if metrics:
        for k, v in metrics.items():
            print(f"  {k}: {v}")
    if error:
        print("Error:", error)
    if success and gif_path:
        print("GIF saved:", gif_path)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
