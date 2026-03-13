import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner

# F-03: 40 seconds at 60 fps
MAX_STEPS_F03 = 40 * 60

def run_stage(stage_index):
    task_name = "Category4_Granular_FluidInteraction.F_03"
    task_module = __import__(
        f"tasks.{task_name}",
        fromlist=["environment", "evaluator", "agent", "renderer"],
    )
    stages_mod = __import__(
        f"tasks.{task_name}.stages",
        fromlist=["get_f03_curriculum_stages"],
    )
    stages = stages_mod.get_f03_curriculum_stages()
    stage = stages[stage_index]
    stage_id = stage["stage_id"]
    
    # Use the specific build_agent and agent_action for this stage
    # We will modify agent.py to have build_agent_stage_1, etc.
    original_build_agent = task_module.agent.build_agent
    original_agent_action = task_module.agent.agent_action
    
    suffix = f"_stage_{stage_index + 1}"
    if hasattr(task_module.agent, f"build_agent{suffix}"):
        task_module.agent.build_agent = getattr(task_module.agent, f"build_agent{suffix}")
    if hasattr(task_module.agent, f"agent_action{suffix}"):
        task_module.agent.agent_action = getattr(task_module.agent, f"agent_action{suffix}")
    
    try:
        env_overrides = {
            "terrain_config": stage.get("terrain_config", {}) or {},
            "physics_config": stage.get("physics_config", {}) or {},
        }
        runner = TaskRunner(task_name, task_module)
        result = runner.run(
            headless=True,
            max_steps=MAX_STEPS_F03,
            save_gif=False,
            env_overrides=env_overrides,
        )
        assert result is not None, f"Stage {stage_id} failed to run"
        score, metrics = result
        print(f"\nStage {stage_id} metrics: {metrics}")
        assert metrics.get("success", False), f"Stage {stage_id} failed: {metrics.get('failure_reason', 'unknown reason')}. Score: {score}"
    finally:
        # Restore original functions
        task_module.agent.build_agent = original_build_agent
        task_module.agent.agent_action = original_agent_action

def test_stage_1():
    run_stage(0)

def test_stage_2():
    run_stage(1)

def test_stage_3():
    run_stage(2)

def test_stage_4():
    run_stage(3)

if __name__ == "__main__":
    # If run directly via python, execute all stages sequentially
    print("Starting verification of all mutated stages...")
    try:
        print("\n--- Testing Stage 1 ---")
        test_stage_1()
        print("Stage 1 Passed!")
        
        print("\n--- Testing Stage 2 ---")
        test_stage_2()
        print("Stage 2 Passed!")
        
        print("\n--- Testing Stage 3 ---")
        test_stage_3()
        print("Stage 3 Passed!")
        
        print("\n--- Testing Stage 4 ---")
        test_stage_4()
        print("Stage 4 Passed!")
        
        print("\n" + "="*30)
        print("ALL STAGES VERIFIED SUCCESSFULLY")
        print("="*30)
    except Exception as e:
        print(f"\nVerification failed: {e}")
        sys.exit(1)
