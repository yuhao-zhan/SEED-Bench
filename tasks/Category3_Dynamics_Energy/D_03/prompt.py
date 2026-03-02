"""
D-03: Phase-Locked Gate (相位锁定门) — Category3_Dynamics_Energy.
"""
from ...primitives_api import (
    API_INTRO,
    ADD_BEAM_08_2,
    BODIES_LIST,
    GET_STRUCTURE_MASS,
    GET_VEHICLE_CABIN,
    SET_MATERIAL_PROPERTIES_STATICS,
)

# D_03: add_joint with cabin/beam only (no ground anchor)
ADD_JOINT_CABIN_ONLY = """
### Add Joint
```python
joint = sandbox.add_joint(body_a, body_b, anchor_point, type='rigid')
```
- `body_a, body_b`: Two bodies to connect. **body_b must be the cart (get_vehicle_cabin()) or another beam**. Ground anchoring (body_b=None) is **not allowed**.
- `anchor_point`: (x, y) connection point in world coordinates
- `type`: `'rigid'` (weld) or `'pivot'` (revolute hinge)
- Returns: Joint object
"""

TASK_PROMPT = {
    "task_description": """
You are designing a **cart** that must pass through **four rotating gates** while satisfying **velocity checkpoints**. The cart starts at x=4 m, y=2.5 m with initial speed 10 m/s to the right.

**Environment**
- **Cart**: Moves right on a track. You attach beams to the cart only (no ground anchors).
- **Four gates** at x=10, 11.5, 11.75, 11.75. Each rod rotates; **open** only during narrow angle windows. Collision when closed → fail.
- **Zones**: Mud [5.5, 7.5] (damping), impulse [8, 9] (one-time backward kick), second impulse [10.5, 11] (one-time backward after gate 1), decel [9.5, 11] (strong damping), brake [12, 15].
- **Design**: Attach beams to the cart. Build zone x∈[4.8, 9.0], y∈[2.0, 3.2].

**Success requires**
- **Speed trap**: v(9) ≥ 2.8 m/s when first crossing x=9.
- **Velocity checkpoint**: v(11) in [1.1, 2.7] m/s when first crossing x=11.
- **Pass all four gates** when each is open (narrow windows).
- **Reach x ≥ 11.75 m** with final speed in [0.45, 2.6] m/s.
""",
    "success_criteria": """
## Success Criteria
1. **Speed trap**: v(9) ≥ 2.8 m/s when first crossing x=9.
2. **Velocity profile**: v(11) in [1.1, 2.7] m/s when first crossing x=11.
3. **No collision**; pass **all four gates** when each is open.
4. Reach **x ≥ 11.75 m** with **final speed** in **[0.45, 2.6] m/s**.
5. Design: ≥4 beams, ≤5 beams, <14 kg, build zone, cart only.

## Failure
- v(9) < 2.8; v(11) outside [1.1, 2.7]; gate collision; did not reach x≥11.75; final speed outside [0.45, 2.6]; design constraints violated.

## Design Constraints
- **Build zone**: x=[4.8, 9.0], y=[2.0, 3.2]. All beam centers must lie inside.
- **Beam limits**: Each beam 0.08 <= width, height <= 2.0 m.
- **Beam count**: 4 <= beams <= 5.
- **Mass**: Total structure mass < 14 kg.
- **No ground anchors**: All joints must connect cabin-to-cabin or cabin-to-beam.
""",
    "primitives_api": API_INTRO
    + ADD_BEAM_08_2
    + ADD_JOINT_CABIN_ONLY
    + GET_VEHICLE_CABIN
    + GET_STRUCTURE_MASS
    + SET_MATERIAL_PROPERTIES_STATICS
    + BODIES_LIST,
}
