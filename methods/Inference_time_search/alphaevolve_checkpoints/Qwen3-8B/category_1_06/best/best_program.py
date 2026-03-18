# EVOLVE-BLOCK-START
def build_agent(sandbox):
    # Precompute harmonic numbers
    H = [0.0] * 21  # H[0] unused
    for i in range(1, 21):
        H[i] = H[i-1] + 1.0 / i
    # Add blocks
    for i in range(1, 21):
        x_center = 0.5 * H[i] - 1.0
        # Block's bottom-left corner is at x_center - 0.5, y=0.0
        block = sandbox.add_block(x=x_center - 0.5, y=0.0, width=1.0, height=0.5)
    return block

def agent_action(sandbox, agent_body, step_count):
    pass
# EVOLVE-BLOCK-END