#!/usr/bin/env python3
"""Generate success GIFs for each mutated stage using the stage reference solutions."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier
from evaluation.evaluate_cross_mutated import get_reference_solution
from tasks.Category2_Kinematics_Linkages.K_01.stages import get_k01_curriculum_stages


def main():
    task_dir = os.path.dirname(os.path.abspath(__file__))
    stages_config = get_k01_curriculum_stages()
    max_steps_mutated = 350000

    for stage in stages_config:
        stage_id = stage['stage_id']
        num = stage_id.split("-")[1]
        gif_path = os.path.join(task_dir, f"stage_{num}_solution_success.gif")
        print(f"Generating GIF for {stage_id} -> {gif_path}...")

        code = get_reference_solution("Category2_Kinematics_Linkages/K_01", stage_id)
        verifier = CodeVerifier(
            task_name="Category2_Kinematics_Linkages/K_01",
            max_steps=max_steps_mutated,
            env_overrides={
                "terrain_config": stage.get("terrain_config", {}),
                "physics_config": stage.get("physics_config", {}),
            },
        )
        success, score, _, error = verifier.verify_code(code=code, headless=True, save_gif_path=gif_path)
        if success:
            print(f"  Success. GIF saved to {gif_path}")
        else:
            print(f"  Failed: score={score}, error={error}")


if __name__ == "__main__":
    main()
