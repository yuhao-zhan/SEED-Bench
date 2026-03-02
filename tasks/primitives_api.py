"""
Centralized Primitives API documentation for DaVinciBench tasks.
Each API is a separate variable. Tasks import only the APIs they need.
Different usages have separate variables (no "task specific" in docs).
"""

API_INTRO = """
## Available Primitives API

**Important**: You may ONLY use the APIs documented below. Do not access internal attributes (e.g. _world, _bodies) or use undocumented methods.
"""

# --- ADD_BEAM variants (by dimension constraint) ---

ADD_BEAM_01_10 = """
### Add Beam
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=1.0)
```
- `x, y`: Beam center position (meters)
- `width, height`: Beam dimensions (meters). **Constraint**: 0.1 <= width, height <= 10.0
- `angle`: Rotation angle (radians, default 0)
- `density`: Density (kg/m³, default 1.0)
- Returns: Beam body object
- Creates a rigid rectangular structural element.
- **Body properties**: The returned body has `fixtures` (list). For deck/road surfaces requiring higher friction: `for f in body.fixtures: f.friction = 0.8`. Bodies also have `angularDamping` and `linearDamping` for oscillation control.
"""

ADD_BEAM_05_5 = """
### Add Beam
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=1.0)
```
- `x, y`: Beam center position (meters)
- `width, height`: Beam dimensions (meters). **Constraint**: 0.05 <= width, height <= 5.0
- `angle`: Rotation angle (radians, default 0)
- `density`: Density (kg/m³, default 1.0)
- Returns: Beam body object
- Creates a rigid rectangular structural element.
"""

ADD_BEAM_05_3 = """
### Add Beam
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=1.0)
```
- `x, y`: Beam center position (meters)
- `width, height`: Beam dimensions (meters). **Constraint**: 0.05 <= width, height <= 3.0
- `angle`: Rotation angle (radians, default 0)
- `density`: Density (kg/m³, default 1.0)
- Returns: Beam body object
- Creates a rigid rectangular structural element.
"""

ADD_BEAM_05_2 = """
### Add Beam
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=1.0)
```
- `x, y`: Beam center position (meters)
- `width, height`: Beam dimensions (meters). **Constraint**: 0.05 <= width, height <= 2.0
- `angle`: Rotation angle (radians, default 0)
- `density`: Density (kg/m³, default 1.0)
- Returns: Beam body object
- Creates a rigid rectangular structural element.
"""

ADD_BEAM_05_4 = """
### Add Beam
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=1.0)
```
- `x, y`: Beam center position (meters)
- `width, height`: Beam dimensions (meters). **Constraint**: 0.05 <= width, height <= 4.0
- `angle`: Rotation angle (radians, default 0)
- `density`: Density (kg/m³, default 1.0)
- Returns: Beam body object
- Creates a rigid rectangular structural element.
"""

ADD_BEAM_01_5 = """
### Add Beam
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=1.0)
```
- `x, y`: Beam center position (meters)
- `width, height`: Beam dimensions (meters). **Constraint**: 0.1 <= width, height <= 5.0
- `angle`: Rotation angle (radians, default 0)
- `density`: Density (kg/m³, default 1.0)
- Returns: Beam body object
- Creates a rigid rectangular structural element.
"""

ADD_BEAM_01_4 = """
### Add Beam
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=1.0)
```
- `x, y`: Beam center position (meters)
- `width, height`: Beam dimensions (meters). **Constraint**: 0.1 <= width, height <= 4.0
- `angle`: Rotation angle (radians, default 0)
- `density`: Density (kg/m³, default 1.0)
- Returns: Beam body object
- Creates a rigid rectangular structural element.
"""

ADD_BEAM_08_2 = """
### Add Beam
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=1.0)
```
- `x, y`: Beam center position (meters)
- `width, height`: Beam dimensions (meters). **Constraint**: 0.08 <= width, height <= 2.0
- `angle`: Rotation angle (radians, default 0)
- `density`: Density (kg/m³, default 1.0)
- Returns: Beam body object
- Creates a rigid rectangular structural element.
"""

ADD_BEAM_01_3 = """
### Add Beam
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=1.0)
```
- `x, y`: Beam center position (meters)
- `width, height`: Beam dimensions (meters). **Constraint**: 0.1 <= width, height <= 3.0
- `angle`: Rotation angle (radians, default 0)
- `density`: Density (kg/m³, default 1.0)
- Returns: Beam body object
- Creates a rigid rectangular structural element.
"""

ADD_BLOCK = """
### Add Block
```python
block = sandbox.add_block(x, y, width, height)
```
- `x, y`: Block center position (meters)
- `width, height`: Block dimensions (meters)
- Returns: Block body object
- Creates a rigid rectangular block. No built-in joints; only gravity and friction.
"""

# S-06 Overhang task: extra constraints for add_block (import only in S_06 prompt)
ADD_BLOCK_S06_EXTRA = """
- **Constraint**: width <= 1.0, height <= 0.5. All blocks must spawn at x < 0 (on table).
- **Note**: In this task, add_joint is DISABLED. Only gravity and friction.
"""

# --- ADD_JOINT variants ---

ADD_JOINT_STATICS = """
### Add Joint
```python
joint = sandbox.add_joint(body_a, body_b, anchor_point, type='rigid')
```
- `body_a, body_b`: Two body objects to connect (from add_beam or terrain bodies).
- `anchor_point`: Connection point position (x, y) tuple (meters)
- `type`: Joint type
  - `'rigid'`: Locks relative rotation (Weld) - use for fixed connections
  - `'pivot'`: Allows free rotation (Hinge) - use for rotating connections
- Returns: Joint object
- **Note**: Some tasks limit anchor count (e.g. max 2 wall anchors). Each wall anchor may have a torque limit.
"""

ADD_JOINT_PIVOT = """
### Add Joint
```python
joint = sandbox.add_joint(body_a, body_b, anchor_point, type='pivot', lower_limit=None, upper_limit=None)
```
- `body_a, body_b`: Two body objects to connect (from add_beam, add_wheel, add_pad)
- `anchor_point`: Connection point position (x, y) tuple (meters)
- `type`: Joint type
  - `'rigid'`: Locks relative rotation (Weld) - use for fixed connections
  - `'pivot'`: Allows free rotation (Revolute) - use for motor-driven joints
- `lower_limit, upper_limit`: Joint angle limits in radians (optional, for pivot joints)
- Returns: Joint object. **Store the return value** for use with set_motor, or use sandbox.joints to find joints after building.
"""

ADD_JOINT_SLIDER = """
### Add Joint (Slider / Prismatic)
For vertical linear motion (e.g. gripper arm up/down), use type='slider':
```python
joint = sandbox.add_joint(base, slider, anchor, type='slider',
    axis=(0, -1), lower_translation=0.0, upper_translation=stroke_meters,
    enable_motor=True, motor_speed=0.0, max_motor_force=5000.0)
```
- `axis=(0, -1)`: Vertical; positive translation = down
- `lower_translation`, `upper_translation`: Stroke limits (meters)
- Drive with `set_slider_motor(joint, speed, max_force)`.
- **Tip**: Set `slider.fixedRotation = True` on the slider beam to keep it vertical (no tilt).
"""

ADD_JOINT_GROUND_ANCHOR = """
### Add Joint
```python
joint = sandbox.add_joint(body_a, body_b, anchor_point, type='rigid')
```
- `body_a, body_b`: Two bodies to connect. Use `body_b=None` to anchor to the ground at anchor_point.
- `anchor_point`: (x, y) connection point in world coordinates
- `type`: `'rigid'` (weld) or `'pivot'` (revolute hinge)
- Returns: Joint object
- **Ground anchor**: When body_b=None, body_a is anchored to the ground. Use for launchers, jumpers, etc.
"""

ADD_SPRING = """
### Add Spring
```python
spring = sandbox.add_spring(body_a, body_b, anchor_a, anchor_b, stiffness, damping)
```
- Creates a spring-damper connection between two bodies.
- `anchor_a, anchor_b`: Local anchor points (x, y) on each body, or (0, 0) for body center
- `stiffness`: Spring stiffness (Hz)
- `damping`: Damping ratio (0-1)
- Use for shock absorbers or tuned mass dampers (TMD).
"""

ADD_SPRING_LAUNCHER = """
### Add Spring
```python
spring = sandbox.add_spring(body_a, body_b, anchor_a, anchor_b, rest_length=None, stiffness=500.0, damping_ratio=0.5)
```
- `body_a, body_b`: Two bodies to connect (e.g. ground and arm). Use sandbox.get_ground() for ground.
- `anchor_a, anchor_b`: (x, y) attachment points on each body in world coordinates
- `rest_length`: Natural length in meters (optional; if None, uses current distance)
- `stiffness`: Spring stiffness in N/m (default 500). **Constraint**: 10 <= stiffness <= 3000
- `damping_ratio`: 0–1 (default 0.5 for moderate damping)
- Use for spring energy storage: pre-tension then release to launch.
"""

GET_GROUND = """
### Get Ground
```python
ground = sandbox.get_ground()
```
- Returns: Ground body for spring attachment, or None
- Use for add_spring(ground, arm, anchor_a, anchor_b, ...) to connect spring between ground and your launcher arm.
"""


GET_PROJECTILE = """
### Get Projectile
```python
projectile = sandbox.get_projectile()
```
- Returns: Projectile body (ball to be launched), or None
- The projectile starts at rest; your launcher must accelerate it toward the target.
"""

GET_JUMPER = """
### Get Jumper
```python
jumper = sandbox.get_jumper()
```
- Returns: Jumper body to be launched, or None
- Use in agent_action to apply impulse via sandbox.apply_impulse_to_jumper(vx, vy).
"""

GET_VEHICLE_CABIN = """
### Get Vehicle Cabin
```python
cabin = sandbox.get_vehicle_cabin()
```
- Returns: Vehicle cabin body for attaching beams. All joints must connect cabin-to-cabin or cabin-to-beam.
- No ground anchors allowed in this task.
"""

GET_SWING_SEAT = """
### Get Swing Seat
```python
seat = sandbox.get_swing_seat()
```
- Returns: Swing seat body. Use apply_force_to_seat(fx, fy) and apply_impulse_to_seat(ix, iy) in agent_action.
- The seat has `position` (x, y) and `linearVelocity` (vx, vy) for reading control logic.
"""

APPLY_IMPULSE_TO_JUMPER = """
### Apply Impulse to Jumper
```python
sandbox.apply_impulse_to_jumper(impulse_x, impulse_y)
```
- Call in agent_action to launch the jumper. impulse_x, impulse_y in N·s (kg·m/s).
- Use once at the appropriate moment (e.g. when mechanism releases).
"""

SET_JUMPER_VELOCITY = """
### Set Jumper Velocity
```python
sandbox.set_jumper_velocity(vx, vy)
```
- Call in agent_action to set jumper velocity (m/s). Use for instant launch (e.g. on first step).
- Equivalent to applying an impulse that results in velocity (vx, vy).
"""

APPLY_FORCE_TO_SEAT = """
### Apply Force to Seat
```python
sandbox.apply_force_to_seat(fx, fy)
```
- Call in agent_action to apply force (N) to the swing seat. Use for pumping.
- **Constraint**: |fx| <= sandbox.MAX_PUMP_FORCE (e.g. 42 N horizontal per step).
"""

APPLY_IMPULSE_TO_SEAT = """
### Apply Impulse to Seat
```python
sandbox.apply_impulse_to_seat(ix, iy)
```
- Call in agent_action to apply impulse (N·s) to the swing seat. Use for initial kick.
"""

GET_WIND_FORCE_AT_TIME = """
### Get Wind Force at Time
```python
fx = sandbox.get_wind_force_at_time(t)
```
- Returns: Horizontal wind force (N) at simulation time t (seconds). Use for wind-aware pumping.
"""

GET_SIM_TIME = """
### Get Simulation Time
```python
t = sandbox.get_sim_time()
```
- Returns: Current simulation time in seconds. Use with get_wind_force_at_time for wind-aware control.
"""

BODIES_LIST = """
### Bodies List
- `sandbox.bodies`: List of all beams you created. Use to access bodies for control (e.g. body.angularVelocity in agent_action).
"""

GET_STRUCTURE_MASS = """
### Get Structure Mass
```python
total_mass = sandbox.get_structure_mass()
```
- Returns: Total mass of all created objects (kg)
- Use to check budget limits (e.g. 2000kg, 120kg).
"""

GET_STRUCTURE_BOUNDS = """
### Get Structure Bounds
```python
bounds = sandbox.get_structure_bounds()
```
- Returns: dict with `top`, `width`, `center_x`, `min_x`, `max_x` (meters)
- Use to verify structure height and width constraints.
"""

GET_STRUCTURE_REACH = """
### Get Structure Reach
```python
max_x = sandbox.get_structure_reach()
```
- Returns: Maximum x position of any structure body (meters)
- Use to verify horizontal extension (e.g. reach >= 14m).
"""

# --- SET_MATERIAL_PROPERTIES variants ---

SET_MATERIAL_PROPERTIES_STATICS = """
### Set Material Properties
```python
sandbox.set_material_properties(body, restitution=0.2)
```
- `body`: Body object from add_beam
- `restitution`: Bounciness (0.0 = clay, 1.0 = superball)
- Low restitution helps absorb impact. Use for impact-absorbing structures.
"""

SET_MATERIAL_PROPERTIES_KINEMATICS = """
### Set Material Properties
```python
sandbox.set_material_properties(body, restitution=0.2, friction=None)
```
- `body`: Body object from add_beam, add_wheel, add_pad
- `restitution`: Bounciness (0.0 = clay, 1.0 = superball)
- `friction`: Friction coefficient (optional). Use for grip (e.g. legs, fingers, pads).
- Low restitution helps absorb impact.
"""

# --- Category2: Kinematics & Linkages ---

ADD_WHEEL_05_08 = """
### Add Wheel
```python
wheel = sandbox.add_wheel(x, y, radius=0.2, density=0.6)
```
- `x, y`: Wheel center position (meters)
- `radius`: Wheel radius (meters). **Constraint**: 0.05 <= radius <= 0.8
- `density`: Density (kg/m³, default 0.6)
- Returns: Wheel body object (circular)
- Attach to chassis with add_joint(..., type='pivot') and drive with set_motor(joint, motor_speed, max_torque).
"""

SET_MOTOR = """
### Set Motor
```python
sandbox.set_motor(joint, motor_speed, max_torque=100.0)
```
- `joint`: Joint object (must be a pivot/revolute joint from add_joint)
- `motor_speed`: Target angular velocity (rad/s, positive = counterclockwise)
- `max_torque`: Maximum motor torque (N·m, default 100.0)
- Use to drive rotating joints (legs, wheels, etc.).
"""

ADD_PAD = """
### Add Pad
```python
pad = sandbox.add_pad(x, y, radius=0.12, density=0.8)
```
- `x, y`: Pad center position (meters)
- `radius`: Pad radius (meters). **Constraint**: 0.05 <= radius <= 0.25
- When active (set_pad_active), pulls toward wall. Each pad has max load limit.
- Returns: Pad body object. Attach to structure with add_joint(..., type='rigid').
"""

SET_PAD_ACTIVE = """
### Set Pad Active
```python
sandbox.set_pad_active(pad, active)
```
- `pad`: Pad body from add_pad
- `active`: True to pull toward wall (stick), False to release
- Use in agent_action to stick when needed, release when moving.
"""

SET_SLIDER_MOTOR = """
### Set Slider Motor
```python
sandbox.set_slider_motor(joint, speed, max_force=5000.0)
```
- `joint`: Prismatic/slider joint from add_joint(type='slider', ...)
- `speed`: Linear velocity (m/s). Positive = extend down, negative = retract up
- `max_force`: Max motor force (N)
- Use for vertical gripper motion.
"""

GET_ANCHOR_FOR_GRIPPER = """
### Get Anchor for Gripper
```python
gantry = sandbox.get_anchor_for_gripper()
```
- Returns: Static gantry body for attaching gripper base, or None
- Weld your gripper base to this body so it does not fall.
"""

GET_OBJECT_CONTACT_COUNT = """
### Get Object Contact Count
```python
num_points, num_bodies = sandbox.get_object_contact_count()
```
- Returns: (num_contact_points, num_gripper_bodies_touching_object)
- Use to detect if object is being grasped (contact_count > 0).
"""

JOINTS_LIST = """
### Joints List
- `sandbox.joints`: List of all created joints. Use to find joint references for set_motor/set_slider_motor if you did not store add_joint return values.
"""

WELD_TO_GLASS = """
### Weld to Glass
```python
sandbox.weld_to_glass(body, anchor_point)
```
- `body`: Body to fix (e.g. wiper base from add_beam)
- `anchor_point`: (x, y) on the glass surface (glass top at y=2.0m)
- Welds the body to the glass so the wiper base stays fixed. Call after creating the base beam. Use `hasattr(sandbox, 'weld_to_glass')` to check availability.
"""

REMOVE_INITIAL_TEMPLATE = """
### Remove Initial Template
```python
if hasattr(sandbox, 'remove_initial_template'):
    sandbox.remove_initial_template()
```
- Call at the start of build_agent to remove the placeholder body. The environment creates a template for visualization; your structure must replace it. If not called, the placeholder may interfere with your mechanism.
"""

# --- Category4: Granular / Fluid Interaction ---

ADD_BEAM_DAM = """
### Add Beam (Dam)
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=500.0)
```
- `x, y`: Beam center (meters). **Three strips**: left x=[12.4, 12.6], middle x=[12.9, 13.1] (at most 1 beam), right x=[13.4, 13.6] (at most 2 beams). y in [0, 7.5].
- `width, height`: **Constraint**: 0.2 <= width <= 0.6 m, 0.2 <= height <= 1.5 m. Beam bottom (y - height/2) must be >= 0.5.
- `density`: kg/m³. Total mass < 380 kg.
- Returns: Beam body. Bodies have `position` (x, y) for anchor calculations.
"""

ADD_JOINT_DAM_NO_ANCHOR = """
### Add Joint (Dam — no floor anchors)
```python
joint = sandbox.add_joint(body_a, body_b, anchor_point, type='rigid')
```
- `body_a, body_b`: Both must be dam beams. **body_b cannot be None** — ZERO floor anchors allowed.
- `anchor_point`: (x, y) connection point (meters).
- `type`: 'rigid' (weld).
- **At most 11 beam-to-beam joints**. Two cross-joints (left–middle, middle–right) required for one connected structure.
- Returns: Joint object.
"""

GET_TERRAIN_JOINT_COUNT = """
### Get Terrain Joint Count
```python
n = sandbox.get_terrain_joint_count()
```
- Returns: Number of joints anchoring to terrain (floor). For F-01 dam: must be 0 (no floor anchors).
"""

ADD_BEAM_15_2 = """
### Add Beam
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=200.0)
```
- `x, y`: Beam center (meters). **Constraint**: 0.15 <= width, height <= 2.0
- `angle`: Rotation (radians), `density`: kg/m³
- Returns: Beam body object
"""

APPLY_FORCE_AMPHIBIAN = """
### Apply Force (Paddling)
```python
sandbox.apply_force(body, force_x, force_y, step_count=step_count)
```
- Apply force (N) to a body. **Capped at ~520 N per body per step.** **Cooldown**: each body can thrust only every 3 steps — pass step_count from agent_action.
- Call from agent_action each step for paddling.
"""

GET_VEHICLE_FRONT_X = """
### Get Vehicle Front X
```python
front_x = sandbox.get_vehicle_front_x()
```
- Returns: Rightmost x position of the vehicle (meters), or None. Use to detect when approaching pillars or target.
"""

ADD_STATIC_BEAM = """
### Add Static Beam
```python
beam = sandbox.add_static_beam(x, y, width, height, angle=0, density=200.0)
```
- Creates a static (non-dynamic) beam. Counts toward mass budget.
- Use for filter bars, sieves, etc.
"""

GET_PARTICLES_SMALL = """
### Get Particles (Small)
```python
particles = sandbox.get_particles_small()
```
- Returns: List of small particle bodies. In agent_action, nudge via `p.ApplyForceToCenter((fx, fy), wake=True)` when p.active.
"""

GET_PARTICLES_MEDIUM = """
### Get Particles (Medium)
```python
particles = sandbox.get_particles_medium()
```
- Returns: List of medium particle bodies. In agent_action, nudge via `p.ApplyForceToCenter((fx, fy), wake=True)` when p.active.
"""

APPLY_FORCE_TO_PARTICLE = """
### Apply Force to Particle
```python
sandbox.apply_force_to_particle(particle, fx, fy)
```
- Apply force (N) to a fluid/granular particle. **Per-step force budget** is enforced (e.g. 3500–8000 N total magnitude). Prioritize which particles to push.
- Use in agent_action for pipeline, filter nudge, etc.
"""

GET_FLUID_PARTICLES = """
### Get Fluid Particles
```python
particles = sandbox.get_fluid_particles()
```
- Returns: List of fluid particle bodies. Use with apply_force_to_particle for pipeline control.
"""

ADD_BEAM_01_1 = """
### Add Beam
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=150.0)
```
- `x, y`: Beam center (meters)
- `width, height`: **Constraint**: 0.1 <= width, height <= 1.0
- Returns: Beam body object
"""

ADD_BEAM_01_15 = """
### Add Beam
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=300.0)
```
- `x, y`: Beam center (meters)
- `width, height`: **Constraint**: 0.1 <= width, height <= 1.5
- Returns: Beam body object
"""

ADD_BEAM_01_12 = """
### Add Beam
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=250.0)
```
- `x, y`: Beam center (meters)
- `width, height`: **Constraint**: 0.1 <= width, height <= 1.2
- Returns: Beam body object
"""

ADD_STATIC_BEAM_08_1 = """
### Add Static Beam
```python
beam = sandbox.add_static_beam(x, y, width, height, angle=0, density=200.0)
```
- Static beam. **Constraint**: 0.08 <= width, height <= 1.0
- Build zone: x=[5.22, 6.88], y=[1.72, 2.38]. At most 6 beams.
"""

# --- F-03 Excavator ---

ADD_ANCHORED_BASE = """
### Add Anchored Base
```python
base = sandbox.add_anchored_base(x, y, width, height, angle=0, density=400.0)
```
- Fixed to the floor at (x, y). **Required at x=-2, y=0** for F-03.
- Returns: Base body for attaching arm via add_revolute_joint.
"""

ADD_REVOLUTE_JOINT = """
### Add Revolute Joint
```python
joint = sandbox.add_revolute_joint(body_a, body_b, (anchor_x, anchor_y), enable_motor=True, motor_speed=0.0, max_motor_torque=100.0)
```
- Creates revolute (hinge) joint. **Store the return value** for agent_action.
- In agent_action: set `joint.motorSpeed` and `joint.motorEnabled` to control rotation.
- Use for Arm (base–arm) and Bucket (arm–scoop). **2 DOF required** (Arm + Bucket).
"""

ADD_SCOOP = """
### Add Scoop
```python
scoop = sandbox.add_scoop(x, y, width, height, angle=0, density=280.0)
```
- L-shaped scoop (back + floor) that holds and carries particles. Automatically registered.
- Attach to arm tip via add_revolute_joint. Use instead of plain bucket for better collection.
"""

HAS_CENTRAL_WALL = """
### Has Central Wall
```python
has_wall = sandbox.has_central_wall()
```
- Returns: True if central wall obstacle is present (arm must lift to clear y=2.2 when crossing x=0).
"""

# --- Category5: Cybernetics & Control ---

# C-01 Cart-Pole
GET_CART_BODY = """
### Get Cart Body
```python
cart = sandbox.get_cart_body()
```
- Returns: Cart body (the controllable body). Use in build_agent.
"""

GET_POLE_ANGLE = """
### Get Pole Angle
```python
angle = sandbox.get_pole_angle()
```
- Returns: Pole angle in radians (0 = upright; positive = tilted right; negative = tilted left).
- **Note**: Sensor may have delay, noise, or bias; readings are not instantaneous.
"""

GET_POLE_ANGULAR_VELOCITY = """
### Get Pole Angular Velocity
```python
omega = sandbox.get_pole_angular_velocity()
```
- Returns: Pole angular velocity in rad/s.
- **Note**: May have different delay than angle; may have noise.
"""

GET_CART_POSITION = """
### Get Cart Position
```python
x = sandbox.get_cart_position()
```
- Returns: Cart x position in meters (along track).
"""

GET_CART_VELOCITY = """
### Get Cart Velocity
```python
vx = sandbox.get_cart_velocity()
```
- Returns: Cart x velocity in m/s.
"""

APPLY_CART_FORCE = """
### Apply Cart Force
```python
sandbox.apply_cart_force(force_x)
```
- Apply horizontal force in Newtons (positive = right, negative = left).
- **Constraint**: Force is clamped to ±450 N. Actuator has rate limit (max change per step) and delay.
- Call each step from agent_action.
"""

# C-02 Lander
GET_LANDER_BODY = """
### Get Lander Body
```python
lander = sandbox.get_lander_body()
```
- Returns: Lander body (pre-built). Use in build_agent.
"""

GET_LANDER_POSITION = """
### Get Lander Position
```python
x, y = sandbox.get_lander_position()
```
- Returns: (x, y) position in meters (lander center).
"""

GET_LANDER_ANGLE = """
### Get Lander Angle
```python
angle = sandbox.get_lander_angle()
```
- Returns: Craft angle in radians (0 = upright).
"""

GET_LANDER_ANGULAR_VELOCITY = """
### Get Lander Angular Velocity
```python
omega = sandbox.get_lander_angular_velocity()
```
- Returns: Angular velocity in rad/s.
"""

GET_GROUND_Y_TOP = """
### Get Ground Y Top
```python
y_top = sandbox.get_ground_y_top()
```
- Returns: Top surface y-coordinate of ground (meters). Use to compute height above ground.
"""

GET_LANDER_SIZE = """
### Get Lander Size
```python
half_width, half_height = sandbox.get_lander_size()
```
- Returns: (half_width, half_height) in meters. Lander is a box; use to compute bottom y for height above ground.
"""

APPLY_THRUST = """
### Apply Thrust
```python
sandbox.apply_thrust(main_thrust, steering_torque)
```
- `main_thrust`: Force in N along craft's up direction (positive = engine fire). Consumes fuel.
- `steering_torque`: Torque in N·m (positive = counterclockwise). Does not consume fuel.
- **Constraint**: main_thrust capped at 600 N; steering_torque capped at ±120 N·m.
- Call each step from agent_action.
"""

GET_REMAINING_FUEL = """
### Get Remaining Fuel
```python
fuel = sandbox.get_remaining_fuel()
```
- Returns: Remaining fuel impulse in N·s (0 = exhausted). Thrust consumes fuel; exhaust = no thrust.
"""

# C-03 Seeker
GET_SEEKER_BODY = """
### Get Seeker Body
```python
seeker = sandbox.get_seeker_body()
```
- Returns: Seeker body (pre-built). Use in build_agent.
"""

GET_SEEKER_POSITION = """
### Get Seeker Position
```python
x, y = sandbox.get_seeker_position()
```
- Returns: (x, y) position in meters.
"""

GET_SEEKER_VELOCITY = """
### Get Seeker Velocity
```python
vx, vy = sandbox.get_seeker_velocity()
```
- Returns: (vx, vy) in m/s.
"""

GET_SEEKER_HEADING = """
### Get Seeker Heading
```python
heading = sandbox.get_seeker_heading()
```
- Returns: Current thrust direction in radians. Thrust is applied only along this direction; heading turns toward commanded direction at limited rate.
"""

GET_TARGET_POSITION = """
### Get Target Position
```python
x, y = sandbox.get_target_position()
```
- Returns: (x, y) target position. Updates only at certain intervals; target velocity not provided—estimate from history.
"""

GET_REMAINING_IMPULSE_BUDGET = """
### Get Remaining Impulse Budget
```python
budget = sandbox.get_remaining_impulse_budget()
```
- Returns: Remaining thrust budget in N·s. Do not exceed total; exhausting fails.
"""

GET_CORRIDOR_BOUNDS = """
### Get Corridor Bounds
```python
x_min, x_max = sandbox.get_corridor_bounds()
```
- Returns: (x_min, x_max) current allowed x-interval. Stay inside at all times.
"""

GET_TERRAIN_OBSTACLES = """
### Get Terrain Obstacles
```python
obstacles = sandbox.get_terrain_obstacles()
```
- Returns: List of (center_x, center_y, half_width, half_height) for obstacles (some may be moving).
"""

GET_LOCAL_WIND = """
### Get Local Wind
```python
ax, ay = sandbox.get_local_wind()
```
- Returns: (ax, ay) external acceleration to compensate in thrust.
"""

APPLY_SEEKER_FORCE = """
### Apply Seeker Force
```python
sandbox.apply_seeker_force(force_x, force_y)
```
- Command desired thrust direction and magnitude. Actual thrust is applied along current heading; heading turns toward (force_x, force_y) at limited rate.
- **Constraint**: Total magnitude capped at 200 N. Call each step.
"""

# C-04 Escaper
GET_AGENT_BODY = """
### Get Agent Body
```python
agent = sandbox.get_agent_body()
```
- Returns: Agent body (pre-built). Use in build_agent.
"""

GET_AGENT_POSITION = """
### Get Agent Position
```python
x, y = sandbox.get_agent_position()
```
- Returns: (x, y) in meters.
"""

GET_AGENT_VELOCITY = """
### Get Agent Velocity
```python
vx, vy = sandbox.get_agent_velocity()
```
- Returns: (vx, vy) in m/s. **Note**: In C-04 Escaper, velocity returns (0, 0) always—infer from position history.
"""

GET_WHISKER_READINGS = """
### Get Whisker Readings
```python
front, left, right = sandbox.get_whisker_readings()
```
- Returns: [front, left, right] distances in meters (0 to 3). Raycast sensors: front (+x), left (+y), right (-y).
"""

APPLY_AGENT_FORCE = """
### Apply Agent Force
```python
sandbox.apply_agent_force(force_x, force_y)
```
- Apply force in Newtons. **Constraint**: Per-axis limit is task-specific (e.g. 80 N for C-04, 50 N for C-05). Call each step.
"""

# C-05 Switches
GET_TRIGGERED_SWITCHES = """
### Get Triggered Switches
```python
triggered = sandbox.get_triggered_switches()
```
- Returns: List of already triggered switches in order (e.g. ['A'], ['A','B']).
"""

GET_NEXT_REQUIRED_SWITCH = """
### Get Next Required Switch
```python
next_switch = sandbox.get_next_required_switch()
```
- Returns: 'A', 'B', 'C', or None if all done.
"""

GET_COOLDOWN_REMAINING = """
### Get Cooldown Remaining
```python
steps = sandbox.get_cooldown_remaining()
```
- Returns: Steps until next zone can accept (0 if ready).
"""

# C-06 Governor
GET_WHEEL_BODY = """
### Get Wheel Body
```python
wheel = sandbox.get_wheel_body()
```
- Returns: Wheel body (pre-built). Use in build_agent.
"""

GET_WHEEL_ANGULAR_VELOCITY = """
### Get Wheel Angular Velocity
```python
omega = sandbox.get_wheel_angular_velocity()
```
- Returns: Angular velocity in rad/s (positive = counterclockwise).
- **Note**: Measurement may be delayed; infer from response if sluggish.
"""

GET_TARGET_SPEED = """
### Get Target Speed
```python
target = sandbox.get_target_speed()
```
- Returns: Target angular speed (rad/s) for this step. May change over time.
"""

APPLY_MOTOR_TORQUE = """
### Apply Motor Torque
```python
sandbox.apply_motor_torque(torque)
```
- Apply motor torque in N·m (positive = counterclockwise).
- **Note**: Very small torque requests may not take effect (deadzone); max torque may depend on speed.
- Call each step from agent_action.
"""

# --- Category6: Exotic Physics ---

# E-01 Inverted Gravity
ADD_JOINT_TERRAIN_ANCHOR = """
### Add Joint (Terrain Anchor)
```python
joint = sandbox.add_joint(body_a, body_b, anchor_point, type='rigid')
```
- `body_a`: First body (required). `body_b`: Second body or None to anchor to terrain.
- `anchor_point`: (x, y) connection point. When body_b=None, anchor position determines which terrain: floor (y near bottom), ceiling (y near top), or walls. Use get_arena_bounds() for (x_min, x_max, y_min, y_max); use y_min for floor anchor, y_max for ceiling anchor.
- `type`: 'rigid' (weld) or 'pivot' (revolute).
- Returns: Joint object.
"""

GET_ARENA_BOUNDS = """
### Get Arena Bounds
```python
x_min, x_max, y_min, y_max = sandbox.get_arena_bounds()
```
- Returns: (x_min, x_max, y_min, y_max) for arena. Use y_min for floor anchor points, y_max for ceiling anchor points.
"""

GET_BUILD_ZONE = """
### Get Build Zone
```python
x_min, x_max, y_min, y_max = sandbox.get_build_zone()
```
- Returns: (x_min, x_max, y_min, y_max) for build zone. Beam centers must lie within this region.
"""

# E-02 Thick Air
GET_CRAFT_POSITION = """
### Get Craft Position
```python
pos = sandbox.get_craft_position()
```
- Returns: (x, y) of craft center, or None.
"""

GET_CRAFT_VELOCITY = """
### Get Craft Velocity
```python
vel = sandbox.get_craft_velocity()
```
- Returns: (vx, vy) in m/s. Use to detect stalls, slip, and steer.
"""

GET_HEAT = """
### Get Heat
```python
heat = sandbox.get_heat()
```
- Returns: Current cumulative thrust usage (N·s). Compare to overheat limit.
"""

GET_OVERHEAT_LIMIT = """
### Get Overheat Limit
```python
limit = sandbox.get_overheat_limit()
```
- Returns: Overheat limit (N·s). Exceeding fails. Use to plan thrust budget.
"""

IS_OVERHEATED = """
### Is Overheated
```python
sandbox.is_overheated()
```
- Returns: True if heat limit exceeded (thrust no longer applied).
"""

APPLY_THRUST_CRAFT = """
### Apply Thrust (Craft)
```python
sandbox.apply_thrust(fx, fy)
```
- Apply force (N) to craft center for the next step. Call once per step.
- Cumulative |thrust|×time adds to heat; stay under overheat limit.
"""

GET_STEP_COUNT = """
### Get Step Count
```python
step = sandbox.get_step_count()
```
- Returns: Current simulation step index. Use to compensate time-varying disturbances.
"""

# E-03 Slippery World
GET_SLED_POSITION = """
### Get Sled Position
```python
pos = sandbox.get_sled_position()
```
- Returns: (x, y) of sled center, or None.
"""

GET_SLED_VELOCITY = """
### Get Sled Velocity
```python
vel = sandbox.get_sled_velocity()
```
- Returns: (vx, vy) in m/s. Use for control and to infer region effects.
"""

GET_CHECKPOINT_B_REACHED = """
### Get Checkpoint B Reached
```python
reached = sandbox.get_checkpoint_b_reached()
```
- Returns: True if sled has entered checkpoint B. Use when task requires A then B then final.
"""

# E-05 Magnet
GET_BODY_POSITION = """
### Get Body Position
```python
pos = sandbox.get_body_position()
```
- Returns: (x, y) of body center, or None.
"""

GET_BODY_VELOCITY = """
### Get Body Velocity
```python
vel = sandbox.get_body_velocity()
```
- Returns: (vx, vy) in m/s. Use to infer effective forces and detect stall.
"""

# E-04 Variable Mass / E-06 Cantilever: getters for build constraints
GET_GROUND_Y_TOP_EXOTIC = """
### Get Ground Y Top
```python
y_top = sandbox.get_ground_y_top()
```
- Returns: Top surface y-coordinate of ground (meters). Use for anchor placement.
"""

GET_SPAN_BOUNDS = """
### Get Span Bounds
```python
left_x, right_x = sandbox.get_span_bounds()
```
- Returns: (left_x, right_x). Structure must span: at least one beam center x ≤ left_x, one ≥ right_x.
"""

GET_STRUCTURE_MASS_LIMIT = """
### Get Structure Mass Limit
```python
limit = sandbox.get_structure_mass_limit()
```
- Returns: Maximum allowed structure mass (kg).
"""

GET_MIN_BEAMS = """
### Get Min Beams
```python
n = sandbox.get_min_beams()
```
- Returns: Minimum number of beams required (task-specific).
"""

GET_MIN_JOINTS = """
### Get Min Joints
```python
n = sandbox.get_min_joints()
```
- Returns: Minimum number of joints required (task-specific).
"""

ADD_BEAM_01_4_EXOTIC = """
### Add Beam (E-04/E-06)
```python
beam = sandbox.add_beam(x, y, width, height, angle=0, density=1.0)
```
- `x, y`: Beam center (meters), within build zone.
- `width, height`: **Constraint**: 0.1 ≤ width, height ≤ 4.0 (meters).
- `angle`: Rotation (radians), `density`: kg/m³. Returns: Beam body object.
"""
