#!/usr/bin/env python3
import sys
import os

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier
from evaluation.evaluate_cross_mutated import get_reference_solution
from tasks.Category2_Kinematics_Linkages.K_01.stages import get_k01_curriculum_stages

def main():
    # Test all stages including Initial
    stages_config = get_k01_curriculum_stages()
    
    all_stages = [
        {
            "stage_id": "Initial",
            "title": "Initial Task",
            "terrain_config": {},
            "physics_config": {}
        }
    ] + stages_config

    print(f"Testing K_01 reference solutions on their respective environments...")
    print("-" * 60)
    
    passed_count = 0
    total_stages = len(all_stages)
    
    for stage in all_stages:
        stage_id = stage['stage_id']
        title = stage.get('title', stage_id)
        print(f"Testing {stage_id}: {title}...")
        
        try:
            code = get_reference_solution("Category2_Kinematics_Linkages/K_01", stage_id)
            
            # Initial and mutated walkers need many steps; Stage-4 (low gravity + mass cap) needs ~350k.
            max_steps = 90000 if stage_id == "Initial" else 350000
            
            verifier = CodeVerifier(
                task_name="Category2_Kinematics_Linkages/K_01",
                max_steps=max_steps,
                env_overrides={
                    "terrain_config": stage.get("terrain_config", {}),
                    "physics_config": stage.get("physics_config", {})
                }
            )
            
            success, score, metrics, error = verifier.verify_code(code=code, headless=True)
            
            print(f"  Result: Success={success}, Score={score:.2f}, Steps={metrics.get('step_count', 'unknown')}")
            if error:
                print(f"  Error: {error}")
            
            if success:
                passed_count += 1
            else:
                if metrics.get('failure_reason'):
                    print(f"  Reason: {metrics['failure_reason']}")
                elif not success:
                    print(f"  Note: Distance traveled: {metrics.get('distance_traveled', 0):.2f}m")
                    
        except Exception as e:
            print(f"  Failed to test {stage_id}: {e}")
            
        print("-" * 60)

    print(f"\nFinal Result: {passed_count}/{total_stages} stages passed.")
    sys.exit(0 if passed_count == total_stages else 1)

if __name__ == "__main__":
    main()
