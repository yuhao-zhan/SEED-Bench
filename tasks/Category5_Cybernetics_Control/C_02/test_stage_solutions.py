import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner

def test_stage(stage_id):
    task_name = "Category5_Cybernetics_Control.C_02"
    
    # Standard import
    from tasks.Category5_Cybernetics_Control.C_02 import environment, evaluator, agent, renderer
    task_module = sys.modules["tasks.Category5_Cybernetics_Control.C_02"]
    
    _stages_module = __import__(f"tasks.{task_name}.stages", fromlist=["get_c02_curriculum_stages"])
    stages = _stages_module.get_c02_curriculum_stages()
    stage = next(s for s in stages if s["stage_id"] == stage_id)
    
    env_overrides = {
        "terrain_config": dict(stage.get("terrain_config", {}) or {}),
        "physics_config": dict(stage.get("physics_config", {}) or {}),
    }

    # Manual patch (use lowercase stage_N so get_reference_solution and agent.py match)
    suffix = stage_id.replace("-", "_").lower()
    build_func = getattr(agent, f"build_agent_{suffix}")
    action_func = getattr(agent, f"agent_action_{suffix}")
    
    agent.build_agent = build_func
    agent.agent_action = action_func

    runner = TaskRunner(task_name, task_module)
    result = runner.run(
        headless=True,
        max_steps=5000,
        save_gif=True,
        env_overrides=env_overrides,
    )
    
    if result:
        score, metrics = result
        print(f"Stage {stage_id} Score: {score}, Success: {metrics.get('success')}")
        if not metrics.get('success'):
            print(f"Failure reason: {metrics.get('failure_reason')}")
            print(f"Metrics: x={metrics.get('lander_x'):.2f}, y={metrics.get('lander_y'):.2f}, vy={metrics.get('lander_vy'):.2f}, angle={metrics.get('lander_angle'):.2f}")
            print(f"Barrier: y_top={metrics.get('barrier_y_top')}, y_bottom={metrics.get('barrier_y_bottom')}")
        return metrics.get("success")
    return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_stage(sys.argv[1])
    else:
        for i in range(1, 5):
            print(f"\n--- Testing Stage-{i} ---")
            test_stage(f"Stage-{i}")
