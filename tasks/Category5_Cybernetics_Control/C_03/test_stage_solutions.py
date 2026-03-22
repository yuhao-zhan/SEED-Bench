#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier
from evaluation.evaluate_cross_mutated import get_reference_solution
from tasks.Category5_Cybernetics_Control.C_03.stages import get_c03_curriculum_stages

def main():
    stages_config = get_c03_curriculum_stages()
    
    all_stages = [
        {
            "stage_id": "Initial",
            "title": "Initial Task",
            "terrain_config": {"target_rng_seed": 123},
            "physics_config": {}
        }
    ]
    for stage in stages_config:
        st = dict(stage)
        st["terrain_config"] = dict(st.get("terrain_config", {}))
        st["terrain_config"]["target_rng_seed"] = 123
        all_stages.append(st)

    print(f"Testing C_03 reference solutions on their respective environments...")
    print("-" * 60)
    
    passed_count = 0
    total_stages = len(all_stages)
    
    for stage in all_stages:
        stage_id = stage['stage_id']
        title = stage.get('title', stage_id)
        print(f"Testing {stage_id}: {title}...")
        
        try:
            code = get_reference_solution("category_5_03", stage_id)
            
            # Using the full path to skip stuck detection if needed (though Stage 1-3 shouldn't need it)
            verifier = CodeVerifier(
                task_name="Category5_Cybernetics_Control/C_03",
                max_steps=10000,
                env_overrides={
                    "terrain_config": stage.get("terrain_config", {}),
                    "physics_config": stage.get("physics_config", {})
                }
            )
            
            success, score, metrics, error = verifier.verify_code(code=code, headless=True)
            
            print(f"  Result: Success={success}, Score={score:.2f}, Steps={metrics.get('step_count', 'unknown')}")
            if not success:
                print(f"  Metrics: {metrics}")
                if error:
                    print(f"  Error: {error}")
            
            if success:
                passed_count += 1
                    
        except Exception as e:
            print(f"  Failed to test {stage_id}: {e}")
            
        print("-" * 60)

    print(f"\nFinal Result: {passed_count}/{total_stages} stages passed.")
    sys.exit(0 if passed_count == total_stages else 1)

if __name__ == "__main__":
    main()
