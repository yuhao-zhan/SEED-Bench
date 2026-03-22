#!/usr/bin/env python3
import sys
import os

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier
from evaluation.evaluate_cross_mutated import get_reference_solution
from tasks.Category4_Granular_FluidInteraction.F_05.stages import get_f05_curriculum_stages

def main():
    # Test all stages including Initial
    stages_config = get_f05_curriculum_stages()
    
    all_stages = [
        {
            "stage_id": "Initial",
            "title": "Initial Task",
            "terrain_config": {},
            "physics_config": {}
        }
    ] + stages_config

    print(f"Testing F_05 reference solutions on their respective environments...")
    print("-" * 60)
    
    passed_count = 0
    total_stages = len(all_stages)
    
    results = []

    for stage in all_stages:
        stage_id = stage['stage_id']
        title = stage.get('title', stage_id)
        print(f"Testing {stage_id}: {title}...")
        
        try:
            code = get_reference_solution("Category4_Granular_FluidInteraction/F_05", stage_id)
            
            verifier = CodeVerifier(
                task_name="Category4_Granular_FluidInteraction/F_05",
                max_steps=10000,
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
                    print(f"  Note: Metrics: {metrics}")
            
            results.append((stage_id, success, score, metrics.get('failure_reason')))
                    
        except Exception as e:
            print(f"  Failed to test {stage_id}: {e}")
            results.append((stage_id, False, 0.0, str(e)))
            
        print("-" * 60)

    print(f"\nFinal Result: {passed_count}/{total_stages} stages passed.")
    
    print("\nSummary:")
    for stage_id, success, score, reason in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {stage_id}: {status} (Score: {score:.2f}) {f'- {reason}' if reason else ''}")

    sys.exit(0 if passed_count == total_stages else 1)

if __name__ == "__main__":
    main()
