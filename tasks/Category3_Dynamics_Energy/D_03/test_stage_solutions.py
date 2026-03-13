#!/usr/bin/env python3
import sys
import os

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier
from tasks.Category3_Dynamics_Energy.D_03.stages import get_d03_curriculum_stages

def get_reference_solution(stage_id):
    """Read specific reference solution from D_03 agent.py"""
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if stage_id == "Initial":
        return content
    
    stage_suffix = stage_id.replace("-", "_").lower()
    
    lines = content.split('\n')
    new_lines = []
    
    # We want to keep imports and anything else NOT in the functions we are replacing
    # and we want to rename the stage-specific ones to the standard names.
    
    in_initial_build = False
    in_initial_action = False
    
    for line in lines:
        if line.startswith("def build_agent(sandbox):"):
            in_initial_build = True
            continue
        if line.startswith("def agent_action(sandbox, agent_body, step_count):"):
            in_initial_action = True
            continue
        
        # Stop skipping if we hit another top-level def
        if line.startswith("def ") and not (line.startswith("def build_agent") or line.startswith("def agent_action")):
            in_initial_build = False
            in_initial_action = False
            
        if in_initial_build or in_initial_action:
            if line.startswith("    ") or line == "":
                continue
            else:
                in_initial_build = False
                in_initial_action = False
        
        if line.startswith(f"def build_agent_{stage_suffix}(sandbox):"):
            new_lines.append("def build_agent(sandbox):")
        elif line.startswith(f"def agent_action_{stage_suffix}(sandbox, agent_body, step_count):"):
            new_lines.append("def agent_action(sandbox, agent_body, step_count):")
        else:
            new_lines.append(line)
            
    return '\n'.join(new_lines)

def main():
    # Test all stages including Initial
    stages_config = get_d03_curriculum_stages()
    
    all_stages = [
        {
            "stage_id": "Initial",
            "title": "Initial Task",
            "terrain_config": {},
            "physics_config": {}
        }
    ] + stages_config

    print(f"Testing D_03 reference solutions on their respective environments...")
    print("-" * 60)
    
    passed_count = 0
    total_stages = len(all_stages)
    
    for stage in all_stages:
        stage_id = stage['stage_id']
        title = stage.get('title', stage_id)
        print(f"Testing {stage_id}: {title}...")
        
        try:
            code = get_reference_solution(stage_id)
            
            verifier = CodeVerifier(
                task_name="Category3_Dynamics_Energy/D_03",
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
                    
        except Exception as e:
            print(f"  Failed to test {stage_id}: {e}")
            
        print("-" * 60)

    print(f"\nFinal Result: {passed_count}/{total_stages} stages passed.")
    sys.exit(0 if passed_count == total_stages else 1)

if __name__ == "__main__":
    main()
