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
    stages_list = task_module.stages.get_d05_curriculum_stages()

    print("\n" + "="*60)
    print("Testing Stage-3: Harder Shell and Damping")
    stage3 = stages_list[2]
    overrides3 = {
        "terrain_config": stage3.get("terrain_config", {}),
        "physics_config": stage3.get("physics_config", {}),
    }

    def build_test_agent3(sandbox):
        pivot_x, pivot_y = 12.0, 7.5
        arm_len = 5.5
        arm_center_y = pivot_y - arm_len / 2
        arm = sandbox.add_beam(x=pivot_x, y=arm_center_y, width=0.26, height=arm_len, angle=0.0, density=28.0)
        sandbox.add_joint(arm, None, (pivot_x, pivot_y), type="pivot")
        head_dist = 5.5
        head = sandbox.add_beam(x=pivot_x, y=pivot_y - head_dist, width=0.55, height=0.55, angle=0.0, density=110.0)
        sandbox.add_joint(arm, head, (pivot_x, pivot_y - head_dist), type="rigid")
        sandbox.set_material_properties(arm, restitution=0.2)
        sandbox.set_material_properties(head, restitution=0.2)
        return head

    # For Stage 3, damping is 0.6. Initial swing at 380 needs to be higher so it arrives at the slot at the same time.
    for init_v in [26.0, 30.0, 34.0, 38.0]:
        print(f"\n--- Stage-3 with init_v={init_v} ---")
        def action_test3(sandbox, agent_body, step_count):
            arm = sandbox.bodies[0] if sandbox.bodies else None
            if not arm: return
            if step_count == 380:
                arm.angularVelocity = init_v
            elif step_count == 398:
                arm.angularVelocity = 2.2
            elif step_count == 408:
                arm.angularVelocity = 24.0

        task_module.agent.build_agent = build_test_agent3
        task_module.agent.agent_action = action_test3
        result = runner.run(headless=True, max_steps=1000, save_gif=False, env_overrides=overrides3)
        if result:
            score, metrics = result
            print(f"Success: {metrics.get('success')} Broken: {metrics.get('shell_broken')} Bar: {metrics.get('hammer_hit_slot_bar')} Wall: {metrics.get('hammer_hit_slot_wall')}")
            if not metrics.get('success'): print(f"Reason: {metrics.get('failure_reason')}")

    print("\n" + "="*60)
    print("Testing Stage-4: Gravity, Shell, Bar Phase and Damping")
    stage4 = stages_list[3]
    overrides4 = {
        "terrain_config": stage4.get("terrain_config", {}),
        "physics_config": stage4.get("physics_config", {}),
    }

    # For Stage 4, slot bar safe window at ~362 (offset = 46)
    # Gravity is -14, damping is 0.35.
    def build_test_agent4(sandbox):
        pivot_x, pivot_y = 12.0, 7.5
        arm_len = 5.5
        arm_center_y = pivot_y - arm_len / 2
        arm = sandbox.add_beam(x=pivot_x, y=arm_center_y, width=0.26, height=arm_len, angle=0.0, density=28.0)
        sandbox.add_joint(arm, None, (pivot_x, pivot_y), type="pivot")
        head_dist = 5.5
        head = sandbox.add_beam(x=pivot_x, y=pivot_y - head_dist, width=0.55, height=0.55, angle=0.0, density=110.0)
        sandbox.add_joint(arm, head, (pivot_x, pivot_y - head_dist), type="rigid")
        sandbox.set_material_properties(arm, restitution=0.2)
        sandbox.set_material_properties(head, restitution=0.2)
        return head

    for init_v in [26.0, 28.0, 30.0, 32.0]:
        for impact_v in [24.0, 28.0]:
            print(f"\n--- Stage-4 with init_v={init_v}, impact_v={impact_v} ---")
            def action_test4(sandbox, agent_body, step_count):
                arm = sandbox.bodies[0] if sandbox.bodies else None
                if not arm: return
                if step_count == 334:
                    arm.angularVelocity = init_v
                elif step_count == 352:
                    arm.angularVelocity = 2.2
                elif step_count == 362:
                    arm.angularVelocity = impact_v

            task_module.agent.build_agent = build_test_agent4
            task_module.agent.agent_action = action_test4
            result = runner.run(headless=True, max_steps=1000, save_gif=False, env_overrides=overrides4)
            if result:
                score, metrics = result
                print(f"Success: {metrics.get('success')} Broken: {metrics.get('shell_broken')} Bar: {metrics.get('hammer_hit_slot_bar')} Wall: {metrics.get('hammer_hit_slot_wall')}")
                if not metrics.get('success'): print(f"Reason: {metrics.get('failure_reason')}")

if __name__ == "__main__":
    main()
