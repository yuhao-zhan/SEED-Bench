#!/usr/bin/env python3
import os
import sys

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier
from tasks.Category3_Dynamics_Energy.D_03.stages import get_d03_curriculum_stages

def read_reference_solution():
    """Read the reference solution from D_03 agent.py"""
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    print("="*80)
    print("Testing Initial Reference Solution on Mutated Tasks (D-03)")
    print("="*80)

    reference_code = read_reference_solution()
    stages = get_d03_curriculum_stages()
    
    results = []
    passed_count = 0

    for stage in stages:
        stage_id = stage['stage_id']
        title = stage['title']
        print(f"\nTesting {stage_id}: {title}...")
        
        env_overrides = {
            "terrain_config": stage.get("terrain_config", {}),
            "physics_config": stage.get("physics_config", {}),
        }

        verifier = CodeVerifier(
            task_name="Category3_Dynamics_Energy/D_03",
            max_steps=10000,
            env_overrides=env_overrides
        )

        success, score, metrics, error = verifier.verify_code(
            code=reference_code,
            headless=True
        )

        print(f"  Result: Success={success}, Score={score:.2f}")
        if error:
            print(f"  Error: {error}")
        if metrics and metrics.get('failure_reason'):
            print(f"  Reason: {metrics['failure_reason']}")

        if success:
            passed_count += 1
        
        results.append((stage_id, success, score))

    print(f"\n{'='*80}")
    print("Summary")
    print(f"{'='*80}")
    for stage_id, success, score in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{stage_id}: {status} (Score: {score:.2f})")
    
    print(f"\nTotal passed: {passed_count}/{len(stages)}")
    
    if passed_count == 0:
        print("\n✅ Confirmed: Initial reference solution fails on all mutated environments.")
    else:
        print(f"\n⚠️  Warning: {passed_count} mutated task(s) passed. Mutation might be too weak.")

    sys.exit(0 if passed_count == 0 else 1)

if __name__ == "__main__":
    main()
