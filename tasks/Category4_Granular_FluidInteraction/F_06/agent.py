"""
F-06: The Pipeline task Agent module.
Reference solution: Push all particles toward target; avoid pits by lifting when near; 55% delivery.
"""
import math

# Target: (18, 22) x (0, 1.5) - match environment (ground-level target)
TARGET_CX = 20.0
TARGET_CY = 0.75
TARGET_X_LO, TARGET_X_HI = 18.0, 22.0
TARGET_Y_LO, TARGET_Y_HI = 0.0, 1.5
# Pits: lift when in danger zone
PIT1_X_LO, PIT1_X_HI = 13.5, 15.5
PIT1_Y_SAFE = 1.5
PIT2_X_LO, PIT2_X_HI = 16.0, 17.5
PIT2_Y_SAFE = 1.2
# Headwind comp when y>3
HEADWIND_COMP = 70.0
# Push toward high point so particles reach target y band (3.5–6)
F_PUSH = 200.0
PUSH_TARGET_Y = 0.75  # target at ground level


def build_agent(sandbox):
    """Minimal structure."""
    b = sandbox.add_beam(6.0, 5.5, 0.2, 0.2, angle=0, density=140.0)
    sandbox.set_material_properties(b, restitution=0.05)
    sandbox.add_joint(b, None, (6.0, 0.0), type='rigid')
    return b


def _priority(p):
    """Target first (hold), then push others toward (20, 6)."""
    x, y = p.position.x, p.position.y
    if TARGET_X_LO <= x <= TARGET_X_HI and TARGET_Y_LO <= y <= TARGET_Y_HI:
        return (0, 0)
    return (1, -x)


def agent_action(sandbox, agent_body, step_count):
    if not hasattr(sandbox, "get_fluid_particles") or not hasattr(sandbox, "apply_force_to_particle"):
        return
    budget = getattr(sandbox, 'FORCE_BUDGET_PER_STEP', 8000.0)
    particles = sandbox.get_fluid_particles()
    if not particles:
        return
    particles.sort(key=_priority)
    used = 0.0
    for p in particles:
        if used >= budget:
            break
        x, y = p.position.x, p.position.y
        # In target: hold + headwind comp
        if TARGET_X_LO <= x <= TARGET_X_HI and TARGET_Y_LO <= y <= TARGET_Y_HI:
            fx = HEADWIND_COMP if y > 3.0 else 0.0
            fy = 60.0
            mag = math.sqrt(fx*fx + fy*fy)
            if used + mag <= budget:
                sandbox.apply_force_to_particle(p, fx, fy)
                used += mag
            continue
        # Push toward (20, 6) - high arc to clear pits
        dx = TARGET_CX - x
        dy = max(PUSH_TARGET_Y - y, 1.0)
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < 0.01:
            continue
        fx = (dx / dist) * F_PUSH
        fy = (dy / dist) * F_PUSH
        if y > 3.0:
            fx += HEADWIND_COMP
        mag = math.sqrt(fx*fx + fy*fy)
        if mag > 0 and used + mag <= budget:
            sandbox.apply_force_to_particle(p, fx, fy)
            used += mag
