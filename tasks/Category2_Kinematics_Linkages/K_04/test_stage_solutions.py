#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier
from evaluation.evaluate_cross_mutated import get_reference_solution
from tasks.Category2_Kinematics_Linkages.K_04.stages import get_k04_curriculum_stages

def main():
    stages_config = get_k04_curriculum_stages()
    
    print(f"Testing K_04 reference solutions on their respective environments...")
    print("-" * 60)
    
    passed_count = 0
    total_stages = len(stages_config)
    
    for stage in stages_config:
        stage_id = stage['stage_id']
        title = stage.get('title', stage_id)
        print(f"Testing {stage_id}: {title}...")
        
        try:
            code = get_reference_solution("Category2_Kinematics_Linkages/K_04", stage_id)
            
            verifier = CodeVerifier(
                task_name="Category2_Kinematics_Linkages/K_04",
                max_steps=60000,
                env_overrides={
                    "terrain_config": stage.get("terrain_config", {}),
                    "physics_config": stage.get("physics_config", {})
                }
            )
            
            gif_path = os.path.join(os.path.dirname(__file__), f"{stage_id.lower().replace('-', '_')}_solution_success.gif")
            success, score, metrics, error = verifier.verify_code(code=code, headless=True, save_gif_path=gif_path)
            
            print(f"  Result: Success={success}, Score={score:.2f}, Steps={metrics.get('step_count', 'unknown')}")
            if error:
                print(f"  Error: {error}")
            
            if success:
                passed_count += 1
                if os.path.isfile(gif_path):
                    print(f"  GIF saved: {gif_path}")
            else:
                if os.path.isfile(gif_path):
                    try:
                        os.remove(gif_path)
                    except OSError:
                        pass
                if metrics.get('failure_reason'):
                    print(f"  Reason: {metrics['failure_reason']}")
                elif not success:
                    print(f"  Note: Metrics: {metrics}")
                    
        except Exception as e:
            print(f"  Failed to test {stage_id}: {e}")
            
        print("-" * 60)

    print(f"\nFinal Result: {passed_count}/{total_stages} stages passed.")
    sys.exit(0 if passed_count == total_stages else 1)

if __name__ == "__main__":
    main()
