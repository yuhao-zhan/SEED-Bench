"""
S-01: The Bridge task environment module
Defines physics world, terrain, API, etc.
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, revoluteJoint, weldJoint)
import math


class Sandbox:
    """Sandbox environment wrapper for S-01: The Bridge
    
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

        # Joint strength thresholds
        self._anchor_max_force = float(physics_config.get("anchor_max_force", 100.0))
        self._anchor_max_torque = float(physics_config.get("anchor_max_torque", 500.0))
        self._joint_max_force = float(physics_config.get("joint_max_force", 80.0))
        self._joint_max_torque = float(physics_config.get("joint_max_torque", 300.0))
        
        # Wind force
        self._wind_force = tuple(physics_config.get("wind_force", (0.0, 0.0)))

        # 1. Initialize physics world (private attributes, solver LLM should not directly access)
        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []  # Private list, prevent direct manipulation
        self._joints = []  # Private list, prevent direct manipulation

        # Track terrain bodies so mutations can adjust fixture properties post-create.
        self._terrain_bodies = {}
        
        # Real-time airborne rotation tracking (checked every physics step)
        # Similar to basic task: prevent vehicle from rotating more than 180 degrees while airborne
        self._tracked_body = None  # Body to track rotation for
        self._last_tracked_angle = None  # Last angle of tracked body (for step-by-step tracking)
        self._airborne_rotation_clockwise = 0.0  # Accumulated clockwise rotation while airborne
        self._airborne_rotation_counterclockwise = 0.0  # Accumulated counterclockwise rotation while airborne
        self._airborne_rotation_exceeded = False  # Flag: True if rotation exceeded 180° in one direction
        self._AIRBORNE_THRESHOLD = 0.5  # Consider airborne if y > cliff_top + this
        self._MAX_AIRBORNE_ROTATION = math.pi  # 180 degrees in radians
        
        # Joint breaking tracking: track peak forces/torques per joint
        self._joint_peak_forces = {}  # joint -> max force seen
        self._joint_peak_torques = {}  # joint -> max torque seen
        
        # For backward compatibility, keep public attributes (but recommend using controlled API)
        self.world = self._world  # Reserved for renderer use
        self.bodies = self._bodies
        self.joints = self._joints
        
        # 2. Generate terrain (configurable)
        self._create_terrain(terrain_config)
        
        # 3. Set build zone and max structure mass (configurable)
        gap_width = float(terrain_config.get("gap_width", 15.0))
        right_cliff_start = 10.0 + gap_width
        self.BUILD_ZONE_X_MIN = 10.0  # Build zone x start
        self.BUILD_ZONE_X_MAX = right_cliff_start + 5.0  # Build zone x end = target position (deck can reach goal)
        self.BUILD_ZONE_Y_MIN = 5.0  # Build zone y start
        self.BUILD_ZONE_Y_MAX = 15.0  # Build zone y end
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 2000.0))  # Maximum total structure mass (kg)
        
        # 4. Create vehicle (testing vehicle that will cross the bridge)
        self._create_vehicle(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """
        Create terrain: left cliff, right cliff, and water (fail zone)
        """
        # Left Cliff: Ends at x=10m, y=10m
        left_cliff_x = 10.0
        left_cliff_y = 10.0
        left_cliff = self._world.CreateStaticBody(
            position=(left_cliff_x / 2, left_cliff_y / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(left_cliff_x / 2, left_cliff_y / 2)),
                friction=0.8,
            ),
        )
        self._terrain_bodies["left_cliff"] = left_cliff
        
        # Gap width is configurable (default 15m: from x=10 to x=25)
        gap_width = float(terrain_config.get("gap_width", 15.0))
        right_cliff_start = left_cliff_x + gap_width
        right_cliff_end = 100.0  # Extend to right
        right_cliff_width = right_cliff_end - right_cliff_start
        right_cliff_y = 10.0
        right_cliff = self._world.CreateStaticBody(
            position=(right_cliff_start + right_cliff_width / 2, right_cliff_y / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(right_cliff_width / 2, right_cliff_y / 2)),
                friction=0.8,
            ),
        )
        self._terrain_bodies["right_cliff"] = right_cliff
        
        # Store gap info for later use
        self._gap_width = gap_width
        self._right_cliff_start = right_cliff_start
        
        # Water (fail zone) at y=0m - represented as a static body for visualization
        water = self._world.CreateStaticBody(
            position=(50, 0),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(50, 0.1)),
                friction=0.0,
                isSensor=True,  # Sensor so objects can pass through
            ),
        )
        self._terrain_bodies["water"] = water

    def _create_vehicle(self, terrain_config: dict):
        """
        Create testing vehicle: 2000kg, wheelbase 3m, spawns at x=5m, moves right at 5 m/s
        """
        vehicle_mass = 2000.0  # kg
        wheelbase = 3.0  # m
        spawn_x = 5.0
        spawn_y = 10.0 + 0.5  # On top of left cliff
        speed = 5.0  # m/s
        
        # Vehicle chassis (rectangular)
        chassis_width = 2.0
        chassis_height = 0.5
        chassis_density = vehicle_mass / (chassis_width * chassis_height)  # Approximate
        
        chassis = self._world.CreateDynamicBody(
            position=(spawn_x, spawn_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(chassis_width/2, chassis_height/2)),
                density=chassis_density,
                friction=0.8,
            )
        )
        chassis.linearVelocity = (speed, 0)
        chassis.linearDamping = self._default_linear_damping
        chassis.angularDamping = self._default_angular_damping
        
        # Vehicle wheels (two wheels, wheelbase apart)
        wheel_radius = 0.4
        wheel_density = 100.0  # Dense wheels
        
        wheel1 = self._world.CreateDynamicBody(
            position=(spawn_x - wheelbase/2, spawn_y - chassis_height/2 - wheel_radius),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=wheel_radius),
                density=wheel_density,
                friction=0.8,
            )
        )
        wheel1.linearVelocity = (speed, 0)
        wheel1.linearDamping = self._default_linear_damping
        wheel1.angularDamping = self._default_angular_damping
        
        wheel2 = self._world.CreateDynamicBody(
            position=(spawn_x + wheelbase/2, spawn_y - chassis_height/2 - wheel_radius),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=wheel_radius),
                density=wheel_density,
                friction=0.8,
            )
        )
        wheel2.linearVelocity = (speed, 0)
        wheel2.linearDamping = self._default_linear_damping
        wheel2.angularDamping = self._default_angular_damping
        
        # Connect wheels to chassis - anchor at wheel center (not top!)
        wheel1_center_x = spawn_x - wheelbase/2
        wheel1_center_y = spawn_y - chassis_height/2 - wheel_radius
        wheel2_center_x = spawn_x + wheelbase/2
        wheel2_center_y = spawn_y - chassis_height/2 - wheel_radius
        
        joint1 = self._world.CreateRevoluteJoint(
            bodyA=chassis,
            bodyB=wheel1,
            anchor=(wheel1_center_x, wheel1_center_y),  # Anchor at wheel center
            collideConnected=False
        )
        joint2 = self._world.CreateRevoluteJoint(
            bodyA=chassis,
            bodyB=wheel2,
            anchor=(wheel2_center_x, wheel2_center_y),  # Anchor at wheel center
            collideConnected=False
        )
        
        self._terrain_bodies["vehicle_chassis"] = chassis
        self._terrain_bodies["vehicle_wheel1"] = wheel1
        self._terrain_bodies["vehicle_wheel2"] = wheel2
        self._vehicle_joints = [joint1, joint2]

    # --- Physical constraint constants (instance-dependent BUILD_ZONE_X_MAX, MAX_STRUCTURE_MASS set in __init__) ---
    MIN_BEAM_SIZE = 0.1  # Minimum beam width/height (meters)
    MAX_BEAM_SIZE = 10.0  # Maximum beam width/height (meters)
    BUILD_ZONE_X_MIN = 10.0
    BUILD_ZONE_Y_MIN = 5.0
    BUILD_ZONE_Y_MAX = 15.0
    MIN_DECK_FRICTION = 0.5

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        """API: Add a beam."""
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_SIZE))
        
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

    def add_joint(self, body_a, body_b, anchor_point, type='rigid'):
        """API: Add a joint."""
        if body_a is None:
            raise ValueError("add_joint: body_a cannot be None.")
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        if body_b is None:
            left_cliff = self._terrain_bodies.get("left_cliff")
            right_cliff = self._terrain_bodies.get("right_cliff")
            mid_x = 10.0 + self._gap_width / 2
            if anchor_x <= mid_x:
                body_b = left_cliff
            else:
                body_b = right_cliff
        if type == 'rigid':
            joint = self._world.CreateWeldJoint(bodyA=body_a, bodyB=body_b, anchor=(anchor_x, anchor_y), collideConnected=False)
        elif type == 'pivot':
            joint = self._world.CreateRevoluteJoint(bodyA=body_a, bodyB=body_b, anchor=(anchor_x, anchor_y), collideConnected=False)
        else:
            raise ValueError(f"Unknown joint type: {type}")
        self._joints.append(joint)
        return joint

    def get_structure_mass(self):
        """API: Returns total mass of created objects"""
        return sum(body.mass for body in self._bodies)

    def set_material_properties(self, body, restitution=0.2):
        """API: Set restitution for a body"""
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    def step(self, time_step):
        """Physics step with constant joint strength thresholds and wind force"""
        # Apply wind force to all dynamic bodies
        if any(self._wind_force):
            for body in self._bodies:
                body.ApplyForceToCenter(self._wind_force, True)
            for body_name in ["vehicle_chassis", "vehicle_wheel1", "vehicle_wheel2"]:
                if body_name in self._terrain_bodies:
                    self._terrain_bodies[body_name].ApplyForceToCenter(self._wind_force, True)

        if self._tracked_body is not None and not self._airborne_rotation_exceeded:
            current_angle = self._tracked_body.angle
            current_y = self._tracked_body.position.y
            cliff_top = 10.0
            is_airborne = current_y > (cliff_top + self._AIRBORNE_THRESHOLD)
            if is_airborne:
                if self._last_tracked_angle is not None:
                    angle_diff = current_angle - self._last_tracked_angle
                    angle_diff_normalized = ((angle_diff + math.pi) % (2 * math.pi)) - math.pi
                    angle_diff_unwrapped = angle_diff if abs(angle_diff) < math.pi else angle_diff_normalized
                    if angle_diff_unwrapped > 1e-6:
                        self._airborne_rotation_counterclockwise += angle_diff_unwrapped
                    elif angle_diff_unwrapped < -1e-6:
                        self._airborne_rotation_clockwise += abs(angle_diff_unwrapped)
                    net_rotation = abs(self._airborne_rotation_counterclockwise - self._airborne_rotation_clockwise)
                    if net_rotation > self._MAX_AIRBORNE_ROTATION:
                        self._airborne_rotation_exceeded = True
            else:
                self._airborne_rotation_clockwise = 0.0
                self._airborne_rotation_counterclockwise = 0.0
            self._last_tracked_angle = current_angle
        
        self._world.Step(time_step, 10, 10)
        
        joints_to_remove = []
        for joint in self._joints:
            try:
                if hasattr(joint, 'GetReactionForce'):
                    force = joint.GetReactionForce(1.0 / 60.0)
                    force_magnitude = math.sqrt(force.x**2 + force.y**2)
                    if joint not in self._joint_peak_forces: self._joint_peak_forces[joint] = 0.0
                    self._joint_peak_forces[joint] = max(self._joint_peak_forces[joint], force_magnitude)
                    
                    torque_magnitude = 0.0
                    if hasattr(joint, 'GetReactionTorque'):
                        torque_magnitude = abs(joint.GetReactionTorque(1.0 / 60.0))
                        if joint not in self._joint_peak_torques: self._joint_peak_torques[joint] = 0.0
                        self._joint_peak_torques[joint] = max(self._joint_peak_torques[joint], torque_magnitude)
                    
                    body_a, body_b = joint.bodyA, joint.bodyB
                    is_anchor = (body_a.type == staticBody or body_b.type == staticBody or
                                 body_a in self._terrain_bodies.values() or body_b in self._terrain_bodies.values())
                    
                    # Use configurable thresholds
                    if is_anchor:
                        max_force, max_torque = self._anchor_max_force, self._anchor_max_torque
                    else:
                        max_force, max_torque = self._joint_max_force, self._joint_max_torque
                    
                    if self._joint_peak_forces[joint] > max_force or self._joint_peak_torques[joint] > max_torque:
                        joints_to_remove.append(joint)
            except Exception: continue
        
        for joint in joints_to_remove:
            try:
                self._world.DestroyJoint(joint)
                if joint in self._joints:
                    self._joints.remove(joint)
                    self._joint_peak_forces.pop(joint, None)
                    self._joint_peak_torques.pop(joint, None)
            except Exception: pass
    
    def set_tracked_body(self, body):
        self._tracked_body = body
        self._last_tracked_angle = body.angle if body else None
        self._airborne_rotation_clockwise = 0.0
        self._airborne_rotation_counterclockwise = 0.0
        self._airborne_rotation_exceeded = False
    
    def get_airborne_rotation_status(self):
        net_rotation = abs(self._airborne_rotation_counterclockwise - self._airborne_rotation_clockwise)
        return {'accumulated': net_rotation, 'exceeded': self._airborne_rotation_exceeded}
    
    def get_terrain_bounds(self):
        gap_width = getattr(self, '_gap_width', 15.0)
        right_cliff_start = getattr(self, '_right_cliff_start', 25.0)
        return {
            "left_cliff": {"x_end": 10.0, "y": 10.0},
            "right_cliff": {"x_start": right_cliff_start, "y": 10.0},
            "gap": {"x_start": 10.0, "x_end": right_cliff_start, "width": gap_width},
            "build_zone": {
                "x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]
            },
            "water_level": 0.0,
            "fail_zone_y": 0.5
        }
    
    def get_vehicle_position(self):
        if "vehicle_chassis" in self._terrain_bodies:
            chassis = self._terrain_bodies["vehicle_chassis"]
            return (chassis.position.x, chassis.position.y)
        return None
    
    def get_vehicle_velocity(self):
        if "vehicle_chassis" in self._terrain_bodies:
            chassis = self._terrain_bodies["vehicle_chassis"]
            return (chassis.linearVelocity.x, chassis.linearVelocity.y)
        return None
