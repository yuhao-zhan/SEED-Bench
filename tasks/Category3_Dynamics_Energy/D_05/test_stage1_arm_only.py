import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner
from tasks.Category3_Dynamics_Energy.D_05 import agent

def main():
    task_name = "Category3_Dynamics_Energy.D_05"
    task_module = __import__(
        f"tasks.{task_name}",
        fromlist=["environment", "evaluator", "agent", "stages"],
    )
    runner = TaskRunner(task_name, task_module)

    stages_mod = task_module.stages
    stages_list = stages_mod.get_d05_curriculum_stages()
    
    # Test Stage 1
    stage1 = stages_list[0]
    overrides = {
        "terrain_config": stage1.get("terrain_config", {}),
        "physics_config": stage1.get("physics_config", {}),
    }

    def build_test_agent(sandbox):
        pivot_x, pivot_y = 12.0, 7.5
        arm_len = 5.5
        arm_center_y = pivot_y - arm_len / 2
        arm = sandbox.add_beam(
            x=pivot_x, y=arm_center_y, width=0.26, height=arm_len, angle=0.0, density=28.0
        )
        sandbox.add_joint(arm, None, (pivot_x, pivot_y), type="pivot")
        head_dist = 5.5
        head = sandbox.add_beam(
            x=pivot_x, y=pivot_y - head_dist, width=0.55, height=0.55, angle=0.0, density=110.0
        )
        sandbox.add_joint(arm, head, (pivot_x, pivot_y - head_dist), type="rigid")
        sandbox.set_material_properties(arm, restitution=0.2)
        sandbox.set_material_properties(head, restitution=0.2)
        return head

    print(f"\n--- Testing Stage-1 ONLY setting arm.angularVelocity ---")
    
    def action_test(sandbox, agent_body, step_count):
        arm = sandbox.bodies[0] if sandbox.bodies else None
        if not arm: return
        if step_count == 380:
            arm.angularVelocity = 26.0
        elif step_count == 398:
            arm.angularVelocity = 2.2
        elif step_count == 408:
            arm.angularVelocity = 24.0 # High impact

    task_module.agent.build_agent = build_test_agent
    task_module.agent.agent_action = action_test
    
    result = runner.run(headless=True, max_steps=1000, save_gif=False, env_overrides=overrides)
    if result:
        score, metrics = result
        print(f"Success: {metrics.get('success')}  Broken: {metrics.get('shell_broken')}  Bar Hit: {metrics.get('hammer_hit_slot_bar')}")
        if not metrics.get('success'):
            print(f"Failed Reason: {metrics.get('failure_reason')}")

if __name__ == "__main__":
    main()
