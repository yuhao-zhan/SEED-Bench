import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier
from evaluation.evaluate_cross_mutated import get_reference_solution
from tasks.Category2_Kinematics_Linkages.K_01.stages import get_k01_curriculum_stages

stages = get_k01_curriculum_stages()

passed_count = 0
for stage in stages:
    stage_id = stage['stage_id']
    print(f"Testing {stage_id}...")
    
    code = get_reference_solution("Category2_Kinematics_Linkages/K_01", stage_id)
    
    verifier = CodeVerifier(
        task_name="Category2_Kinematics_Linkages/K_01",
        max_steps=6000,
        env_overrides={
            "terrain_config": stage.get("terrain_config", {}),
            "physics_config": stage.get("physics_config", {})
        }
    )
    
    success, score, metrics, error = verifier.verify_code(code=code, headless=True)
    print(f"Result for {stage_id}: Success={success}, Score={score:.2f}")
    if error: print(f"Error: {error}")
    print(f"Metrics: {metrics}")
    print("-" * 50)
    if success:
        passed_count += 1

print(f"Total passed: {passed_count}/{len(stages)}")
if passed_count < len(stages):
    sys.exit(1)
