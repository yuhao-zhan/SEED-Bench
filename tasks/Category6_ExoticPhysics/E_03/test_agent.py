#!/usr/bin/env python3
"""Run E_03 agent via verifier and save GIF."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from evaluation.verifier import CodeVerifier


def main():
    task_name = "Category6_ExoticPhysics/E_03"
    max_steps = 10000
    agent_path = os.path.join(os.path.dirname(__file__), "agent.py")
    with open(agent_path, "r") as f:
        code = f.read()

    verifier = CodeVerifier(task_name=task_name, max_steps=max_steps)
    gif_path = os.path.join(os.path.dirname(__file__), "reference_solution_success.gif")
    success, score, metrics, error = verifier.verify_code(
        code, headless=True, save_gif_path=gif_path
    )
    print("Success:", success)
    print("Score:", score)
    print("Metrics:", metrics)
    if error:
        print("Error:", error)
    print("GIF saved to:", gif_path)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
