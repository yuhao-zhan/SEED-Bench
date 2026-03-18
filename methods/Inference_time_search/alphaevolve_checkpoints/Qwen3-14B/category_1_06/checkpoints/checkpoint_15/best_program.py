# EVOLVE-BLOCK-START
def build_agent(sandbox):
    # Calculate initial x position for the first block to ensure the combined center of mass is at x=0
    # Using 20 blocks, each shifted by 0.49m
    n = 20
    d = 0.49
    x_initial = -d * (n - 1) / 2  # x_initial = -0.49 * 19 / 2 = -4.655
    blocks = []
    x = x_initial
    for i in
# EVOLVE-BLOCK-END