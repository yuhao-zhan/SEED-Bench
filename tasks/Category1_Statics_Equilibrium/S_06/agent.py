import math

def build_agent(sandbox):
    sandbox.add_block(-0.5, 0.11, 1.0, 0.2)
    sandbox.add_block(-0.4, 0.31, 1.0, 0.2)
    return None

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    sandbox.add_block(-0.6, 0.11, 1.0, 0.2, density=100.0)
    sandbox.add_block(-0.35, 0.31, 1.0, 0.2, density=50.0)
    sandbox.add_block(0.0, 0.51, 1.0, 0.2, density=20.0)
    sandbox.add_block(0.3, 0.71, 1.0, 0.2, density=10.0)
    return None

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def build_agent_stage_2(sandbox):
    for x in range(-5, 0):
        sandbox.add_block(x + 0.5, 0.11, 1.0, 0.2, density=1000.0)
    for x in range(-5, 0):
        sandbox.add_block(x + 0.9, 0.31, 1.0, 0.2, density=1000.0)
    sandbox.add_block(0.1, 0.51, 1.0, 0.2, density=100.0)
    sandbox.add_block(0.3, 0.71, 1.0, 0.2, density=50.0)
    sandbox.add_block(0.5, 0.91, 1.0, 0.2, density=10.0)
    return None

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def build_agent_stage_3(sandbox):
    for x in range(-5, 0):
        sandbox.add_block(x + 0.5, 0.11, 1.0, 0.2, density=1000.0)
    for x in range(-5, 0):
        sandbox.add_block(x + 0.8, 0.31, 1.0, 0.2, density=1000.0)
    for x in range(-5, 0):
        sandbox.add_block(x + 1.1, 0.51, 1.0, 0.2, density=1000.0)
    sandbox.add_block(0.3, 0.71, 1.0, 0.2, density=100.0)
    sandbox.add_block(0.5, 0.91, 1.0, 0.2, density=50.0)
    sandbox.add_block(0.7, 1.11, 1.0, 0.2, density=10.0)
    return None

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    for x in range(-5, 0):
        sandbox.add_block(x + 0.5, 0.11, 1.0, 0.2, density=1000.0)
    for x in range(-5, 0):
        sandbox.add_block(x + 0.8, 0.31, 1.0, 0.2, density=1000.0)
    for x in range(-5, 0):
        sandbox.add_block(x + 1.1, 0.51, 1.0, 0.2, density=1000.0)
    for x in range(-5, 0):
        sandbox.add_block(x + 1.4, 0.71, 1.0, 0.2, density=1000.0)
    sandbox.add_block(0.6, 0.91, 1.0, 0.2, density=100.0)
    sandbox.add_block(0.8, 1.11, 1.0, 0.2, density=50.0)
    sandbox.add_block(1.0, 1.31, 1.0, 0.2, density=10.0)
    return None

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
