
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier
from evaluation.feedback import format_feedback
import importlib.util

def test_full_pipeline():
    # Load stages
    stages_path = os.path.join(os.path.dirname(__file__), 'stages.py')
    spec = importlib.util.spec_from_file_location("stages", stages_path)
    stages_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stages_mod)
    stages = stages_mod.get_s06_curriculum_stages()
    
    stage = stages[0] # Stage-1
    
    # Read reference solution (which should fail Stage-1)
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    task_name = "Category1_Statics_Equilibrium/S_06"
    env_overrides = {
        "terrain_config": stage.get("terrain_config", {}),
        "physics_config": stage.get("physics_config", {}),
    }
    
    verifier = CodeVerifier(task_name=task_name, env_overrides=env_overrides)
    success, score, metrics, error = verifier.verify_code(code)
    
    print(f"Verifier success: {success}, score: {score}")
    
    # Generate feedback
    feedback = format_feedback(
        metrics=metrics,
        score=score,
        success=success,
        failed=metrics.get('failed', False),
        failure_reason=metrics.get('failure_reason'),
        task_name=task_name,
        include_suggestions=True
    )
    
    print("\n--- GENERATED FEEDBACK ---")
    print(feedback)
    print("--- END FEEDBACK ---")

if __name__ == "__main__":
    test_full_pipeline()
