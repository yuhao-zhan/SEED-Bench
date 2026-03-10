import math
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from evaluation.verifier import CodeVerifier

stage_1_config = {
    "terrain_config": {
        "object": {"center_of_mass_offset": [0.1, 0.2]}
    },
    "physics_config": {"do_sleep": False}
}
code_stage_1 = """
_stage_1_booster = None
def build_agent(sandbox):
    global _stage_1_booster
    chassis_y = 1.6
    chassis_x = 5.0
    chassis = sandbox.add_beam(x=chassis_x, y=chassis_y, width=2.0, height=0.2, density=2.0)
    sandbox.set_fixed_rotation(chassis, True)
    _stage_1_booster = sandbox.add_beam(x=chassis_x, y=chassis_y, width=0.4, height=0.4, density=100.0)
    sandbox.add_joint(chassis, _stage_1_booster, (chassis_x, chassis_y), type='rigid')
    
    mast = sandbox.add_beam(x=chassis_x + 1.0, y=2.4, width=0.2, height=1.6, density=1.0)
    sandbox.add_joint(chassis, mast, (chassis_x + 1.0, 1.6), type='rigid')
    
    hook = sandbox.add_beam(x=chassis_x + 1.5, y=3.1, width=1.0, height=0.2, density=1.0)
    sandbox.add_joint(mast, hook, (chassis_x + 1.0, 3.1), type='rigid')
    return chassis

def agent_action(sandbox, agent_body, step_count):
    global _stage_1_booster
    if _stage_1_booster: _stage_1_booster.linearVelocity = (4.0, 0.0)
"""

stage_2_config = {
    "terrain_config": {"ground_friction": 1.5, "object": {"mass": 60.0}},
    "physics_config": {"do_sleep": False}
}
code_stage_2 = """
_stage_2_booster = None
def build_agent(sandbox):
    global _stage_2_booster
    chassis_x = 5.0
    chassis_y = 2.0
    
    plate = sandbox.add_beam(x=chassis_x + 1.0, y=2.0, width=0.4, height=2.0, density=10.0)
    sandbox.set_fixed_rotation(plate, True)
    
    _stage_2_booster = sandbox.add_beam(x=chassis_x, y=2.0, width=0.5, height=0.5, density=100.0)
    sandbox.add_joint(plate, _stage_2_booster, (chassis_x, 2.0), type='rigid')
    
    w1 = sandbox.add_wheel(x=chassis_x, y=1.5, radius=0.6, density=5.0)
    sandbox.add_joint(plate, w1, (chassis_x, 1.5), type='pivot')
    
    return plate

def agent_action(sandbox, agent_body, step_count):
    global _stage_2_booster
    if _stage_2_booster: _stage_2_booster.linearVelocity = (4.0, 0.0)
"""

for i, (cfg, code) in enumerate([
    (stage_1_config, code_stage_1),
    (stage_2_config, code_stage_2)
], 1):
    print(f"Testing Stage {i}")
    v = CodeVerifier(task_name="Category2_Kinematics_Linkages/K_04", max_steps=60000, env_overrides=cfg)
    s, sc, m, e = v.verify_code(code=code, headless=True)
    print(f"Result: Success={s}, Score={sc:.2f}, Error={e}")
    if m: print(f"Distance: {m.get('distance_pushed', 0):.2f}, Reason: {m.get('failure_reason')}")
