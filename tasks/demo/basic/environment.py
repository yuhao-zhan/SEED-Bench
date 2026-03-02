"""
Basic task environment module
Defines physics world, terrain, API, etc.
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, revoluteJoint)
import math


class DaVinciSandbox:
    """DaVinci Sandbox environment wrapper
    
    Security design: Hide underlying physics engine objects to prevent solver LLM from bypassing constraint checks
    """
    
    def __init__(self, *, terrain_config=None, physics_config=None):
        """
        Create a sandbox environment.

        Mutated tasks can pass in terrain_config / physics_config to change environment
        WITHOUT exposing the exact changes to the solver agent (the solver only sees feedback).
        """
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        # Store configs for evaluator/renderer introspection (solver does not see these).
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.0))

        # 1. Initialize physics world (private attributes, solver LLM should not directly access)
        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []  # Private list, prevent direct manipulation
        self._joints = []  # Private list, prevent direct manipulation

        # Track terrain bodies so mutations can adjust fixture properties post-create.
        # Dict keys: 'ground', 'obstacles' (list), optionally other named terrain pieces.
        self._terrain_bodies = {'obstacles': []}
        
        # Real-time airborne rotation tracking (checked every physics step)
        self._tracked_body = None  # Body to track rotation for
        self._last_tracked_angle = None  # Last angle of tracked body (for step-by-step tracking)
        self._airborne_rotation_clockwise = 0.0  # Accumulated clockwise rotation while airborne
        self._airborne_rotation_counterclockwise = 0.0  # Accumulated counterclockwise rotation while airborne
        self._airborne_rotation_exceeded = False  # Flag: True if rotation exceeded 180° in one direction
        self._AIRBORNE_THRESHOLD = 0.5  # Consider airborne if y > GROUND_TOP + this
        self._MAX_AIRBORNE_ROTATION = 3.14159265359  # 180 degrees in radians
        
        # For backward compatibility, keep public attributes (but recommend using controlled API)
        # Note: These attributes are mainly for renderer and evaluator, not for solver LLM
        self.world = self._world  # Reserved for renderer use
        self.bodies = self._bodies
        self.joints = self._joints
        
        # 2. Generate terrain (configurable)
        self._create_terrain(terrain_config)

    def _set_body_friction(self, body, friction: float):
        """Set friction for all fixtures on a body."""
        try:
            for fixture in getattr(body, "fixtures", []) or []:
                fixture.friction = float(friction)
        except Exception:
            # Best-effort: if Box2D bindings differ, ignore.
            pass

    def _create_ground_segment(self, *, x_center: float, half_width: float, friction: float):
        """Create a flat ground segment: bottom y=0, top y=1.0."""
        body = self._world.CreateStaticBody(
            position=(x_center, 0.5),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(half_width, 0.5)),
                friction=float(friction),
            ),
        )
        return body

    def _create_terrain(self, terrain_config: dict):
        """
        Terrain config schema (all optional):
          - ground_friction: float
          - obstacle_friction: float
          - obstacle_1: {x, height, angle}
          - obstacle_2: {x, height, angle}
          - gap: {x_start, x_end, depth}  (depth is used only for visualization/semantics; Box2D has no 'hole')
        """
        ground_friction = float(terrain_config.get("ground_friction", 0.8))
        obstacle_friction = float(terrain_config.get("obstacle_friction", ground_friction))

        # Ground: default is one wide segment. If a gap is provided, create two segments.
        gap = terrain_config.get("gap", None)
        if gap and isinstance(gap, dict) and "x_start" in gap and "x_end" in gap:
            x_start = float(gap["x_start"])
            x_end = float(gap["x_end"])

            # Left segment covers [0, x_start]
            left_half_width = max(0.01, x_start / 2.0)
            left_center = left_half_width
            ground_left = self._create_ground_segment(
                x_center=left_center, half_width=left_half_width, friction=ground_friction
            )

            # Right segment covers [x_end, 100] (keep consistent with original 100m-wide floor)
            right_start = x_end
            right_end = 100.0
            right_half_width = max(0.01, (right_end - right_start) / 2.0)
            right_center = right_start + right_half_width
            ground_right = self._create_ground_segment(
                x_center=right_center, half_width=right_half_width, friction=ground_friction
            )

            # Keep a reference for renderer/evaluator; pick the left segment as "ground".
            self.ground = ground_left
            self._terrain_bodies["ground_left"] = ground_left
            self._terrain_bodies["ground_right"] = ground_right
        else:
            # Original: one wide floor centered at x=0 with half-width 50 -> covers [-50, 50].
            self.ground = self._world.CreateStaticBody(
                position=(0, 0.5),
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(50, 0.5)),  # width 100m, height 1m
                    friction=float(ground_friction),
                ),
            )

        self._terrain_bodies["ground"] = self.ground

        # Obstacles
        obstacle_1 = terrain_config.get("obstacle_1", {"x": 15, "height": 2.0, "angle": 0.2})
        obstacle_2 = terrain_config.get("obstacle_2", {"x": 25, "height": 3.0, "angle": -0.3})
        obstacles = [obstacle_1, obstacle_2]
        created = []
        for obs in obstacles:
            x = float(obs.get("x", 0.0))
            height = float(obs.get("height", 2.0))
            angle = float(obs.get("angle", 0.0))

            # Match original widths: obstacle_1 width 4m, obstacle_2 width 6m by default.
            # If custom, use width ~= 2*height as a reasonable default but keep deterministic.
            if obs is obstacle_1:
                half_width = 2.0
            elif obs is obstacle_2:
                half_width = 3.0
            else:
                half_width = max(0.5, height)

            half_height = max(0.1, height / 2.0)
            y_center = self.GROUND_TOP + half_height

            body = self._world.CreateStaticBody(
                position=(x, y_center),
                angle=angle,
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(half_width, half_height)),
                    friction=float(obstacle_friction),
                ),
            )
            created.append(body)

        self._terrain_bodies["obstacles"] = created

    # --- Physical constraint constants ---
    GROUND_TOP = 1.0  # Ground top y coordinate
    MIN_WHEEL_RADIUS = 0.3  # Minimum wheel radius (meters)
    MAX_WHEEL_RADIUS = 2.0  # Maximum wheel radius (meters)
    MAX_CHASSIS_HEIGHT = 1.0  # Maximum chassis height (meters)
    MAX_CONNECTION_DISTANCE = 5.0  # Maximum connection distance (meters)
    MAX_WHEELS = 2  # Maximum number of wheels allowed
    MAX_MOTOR_SPEED = 50.0  # Maximum motor speed (rad/s), range [-50, 50]
    MAX_MOTOR_TORQUE = 2000.0  # Maximum motor torque (N·m), range [0, 2000]

    # --- Below are Primitives API open to LLM (with physical constraints) ---

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        """
        API: Add a beam (Beam/Chassis)
        Note: Design constraints are checked by evaluator, not at API level
        """
        body = self._world.CreateDynamicBody(
            position=(x, y),
            angle=angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(width/2, height/2)),
                density=density,
                friction=0.5,
            )
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

    def add_wheel(self, x, y, radius, density=1.0, friction=0.8):
        """
        API: Add a wheel
        Note: Design constraints are checked by evaluator, not at API level
        """
        body = self._world.CreateDynamicBody(
            position=(x, y),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=radius),
                density=density,
                friction=friction,
            )
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

    def connect(self, body_a, body_b, anchor_x, anchor_y, motor_speed=0.0, max_torque=0.0):
        """
        API: Connect two components (Joint/Actuator)
        Note: Design constraints are checked by evaluator, not at API level
        """
        anchor_world = (anchor_x, anchor_y)
        joint = self._world.CreateRevoluteJoint(
            bodyA=body_a,
            bodyB=body_b,
            anchor=anchor_world,
            enableMotor=(max_torque > 0),
            maxMotorTorque=max_torque,
            motorSpeed=motor_speed,
            collideConnected=False
        )
        self._joints.append(joint)
        return joint

    def step(self, time_step):
        """Physics step"""
        # Note: Design constraints are checked by evaluator, not at runtime
        self._world.Step(time_step, 10, 10)
        
        # Real-time airborne rotation tracking (every physics step!)
        if self._tracked_body is not None and not self._airborne_rotation_exceeded:
            current_y = self._tracked_body.position.y
            current_angle = self._tracked_body.angle
            is_airborne = current_y > (self.GROUND_TOP + self._AIRBORNE_THRESHOLD)
            
            if is_airborne:
                if self._last_tracked_angle is not None:
                    # Calculate angle change from last step
                    # Box2D angles are continuous (can exceed 2π), so we can directly subtract
                    angle_diff = current_angle - self._last_tracked_angle
                    
                    # Handle potential wrapping (though Box2D angles shouldn't wrap)
                    # Normalize to [-pi, pi] to get the shortest angular distance
                    angle_diff_normalized = ((angle_diff + math.pi) % (2 * math.pi)) - math.pi
                    
                    # If the difference is small (< π), use actual (Box2D is continuous)
                    # If large, might have wrapped, use normalized
                    if abs(angle_diff) < math.pi:
                        angle_diff_unwrapped = angle_diff
                    else:
                        # Large jump, might have wrapped - but this shouldn't happen in Box2D
                        # Use normalized to be safe
                        angle_diff_unwrapped = angle_diff_normalized
                    
                    # Accumulate rotation in each direction
                    # Track both clockwise and counterclockwise rotations separately
                    if angle_diff_unwrapped > 1e-6:  # Small threshold to ignore noise
                        # Counterclockwise rotation (positive)
                        self._airborne_rotation_counterclockwise += angle_diff_unwrapped
                    elif angle_diff_unwrapped < -1e-6:  # Small threshold to ignore noise
                        # Clockwise rotation (negative, store as positive)
                        self._airborne_rotation_clockwise += abs(angle_diff_unwrapped)
                    # If angle_diff is very small (near zero), don't accumulate (noise)
                    
                    # Calculate net rotation: the absolute difference between clockwise and counterclockwise
                    # This represents the actual "flip" - if vehicle rotates CCW then CW back, they cancel
                    net_rotation = abs(self._airborne_rotation_counterclockwise - self._airborne_rotation_clockwise)
                    
                    # Check if net rotation exceeded 180 degrees (true flip)
                    if net_rotation > self._MAX_AIRBORNE_ROTATION:
                        self._airborne_rotation_exceeded = True
            else:
                # Reset when on ground
                self._airborne_rotation_clockwise = 0.0
                self._airborne_rotation_counterclockwise = 0.0
            
            # Always update last angle
            self._last_tracked_angle = current_angle
    
    def set_tracked_body(self, body):
        """Set the body to track for airborne rotation"""
        self._tracked_body = body
        self._last_tracked_angle = body.angle if body else None
        self._airborne_rotation_clockwise = 0.0
        self._airborne_rotation_counterclockwise = 0.0
        self._airborne_rotation_exceeded = False
    
    def get_airborne_rotation_status(self):
        """Get airborne rotation tracking status"""
        # Return the net rotation (absolute difference between clockwise and counterclockwise)
        net_rotation = abs(self._airborne_rotation_counterclockwise - self._airborne_rotation_clockwise)
        return {
            'accumulated': net_rotation,  # Net rotation (true flip amount)
            'exceeded': self._airborne_rotation_exceeded
        }
    
    def validate_design(self, chassis_body):
        """
        Validate design completeness (not constraints - constraints are checked by evaluator)
        Returns: (is_valid, errors)
        Note: This method only checks design completeness (e.g., wheels connected, has power source).
        All design constraints (wheel count, dimensions, etc.) are checked by evaluator.
        """
        errors = []
        
        # Check if all wheels are connected
        wheels = [b for b in self._bodies if b != chassis_body and b.type == dynamicBody]
        if len(wheels) == 0:
            errors.append("Design must have at least one wheel")
        
        # Check if each wheel is connected to chassis
        connected_wheels = set()
        for joint in self._joints:
            if joint.bodyA == chassis_body:
                connected_wheels.add(joint.bodyB)
            elif joint.bodyB == chassis_body:
                connected_wheels.add(joint.bodyA)
        
        unconnected_wheels = [w for w in wheels if w not in connected_wheels]
        if unconnected_wheels:
            errors.append(f"{len(unconnected_wheels)} wheels not connected to chassis")
        
        # Check if there is power source (at least one motor)
        if len(self._joints) == 0:
            errors.append("Design must have at least one connection (joint)")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def get_agent_position(self, agent_body):
        """Get Agent position (for evaluation)"""
        return (agent_body.position.x, agent_body.position.y)
    
    def get_terrain_bounds(self):
        """Get terrain bounds (for evaluation)"""
        # Ground starts from x=0, width 50m (task target is x=30m).
        # Obstacles are configurable via terrain_config.
        obstacle_1 = self._terrain_config.get("obstacle_1", {"x": 15, "height": 2, "angle": 0.2})
        obstacle_2 = self._terrain_config.get("obstacle_2", {"x": 25, "height": 3, "angle": -0.3})
        bounds = {
            "start": 0,
            "end": 50,
            "obstacles": [
                {"x": float(obstacle_1.get("x", 15)), "height": float(obstacle_1.get("height", 2)), "angle": float(obstacle_1.get("angle", 0.2))},
                {"x": float(obstacle_2.get("x", 25)), "height": float(obstacle_2.get("height", 3)), "angle": float(obstacle_2.get("angle", -0.3))},
            ],
        }
        gap = self._terrain_config.get("gap", None)
        if isinstance(gap, dict) and "x_start" in gap and "x_end" in gap:
            bounds["gap"] = {
                "x_start": float(gap["x_start"]),
                "x_end": float(gap["x_end"]),
                "depth": float(gap.get("depth", -10)),
            }
        return bounds
