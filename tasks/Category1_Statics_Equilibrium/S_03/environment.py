"""
S-03: The Cantilever task environment module
"""
import Box2D
from Box2D.b2 import (world, polygonShape, staticBody, dynamicBody, revoluteJoint, weldJoint)
import math


class DaVinciSandbox:
    """DaVinci Sandbox environment wrapper for S-03: The Cantilever"""
    
    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.0))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}
        self._wall_joints = []  # Track wall anchor joints
        # Instance-level overridable constraints / task parameters
        self._target_reach = float(terrain_config.get("target_reach", self.TARGET_REACH))
        self._max_anchor_points = int(terrain_config.get("max_anchor_points", self.MAX_ANCHOR_POINTS))
        self._max_anchor_torque = float(terrain_config.get("max_anchor_torque", self.MAX_ANCHOR_TORQUE))
        
        # New mutated mechanics
        self._obstacle_active = terrain_config.get("obstacle_active", False)
        self._obstacle_rect = terrain_config.get("obstacle_rect", [6.0, -1.0, 8.0, 2.5]) # [xmin, ymin, xmax, ymax]
        
        self._drop_load = terrain_config.get("drop_load", False)
        self._drop_mass = float(terrain_config.get("drop_mass", 500.0))
        self._drop_x = float(terrain_config.get("drop_x", 7.5))
        self._drop_y = float(terrain_config.get("drop_y", 12.0))
        self._drop_time = float(terrain_config.get("drop_time", 8.0))
        
        self._forbidden_anchor_y = terrain_config.get("forbidden_anchor_y", None) # [ymin, ymax]
        
        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints
        
        self._create_terrain(terrain_config)
        self._setup_load(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """Create vertical static wall at x=0 and optional obstacles"""
        wall = self._world.CreateStaticBody(
            position=(0, 10),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(0.5, 10)),
                friction=0.8,
            ),
        )
        self._terrain_bodies["wall"] = wall
        
        if self._obstacle_active:
            xmin, ymin, xmax, ymax = self._obstacle_rect
            cx = (xmin + xmax) / 2.0
            cy = (ymin + ymax) / 2.0
            hw = (xmax - xmin) / 2.0
            hh = (ymax - ymin) / 2.0
            obstacle = self._world.CreateStaticBody(
                position=(cx, cy),
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(hw, hh)),
                    friction=0.5,
                ),
            )
            self._terrain_bodies["obstacle"] = obstacle

    def _setup_load(self, terrain_config: dict):
        """Setup two loads: tip load at t=5s, mid-span load at t=10s or dropped at t=8s"""
        self._load_mass = float(terrain_config.get("load_mass", self.LOAD_MASS))
        self._load_attach_time = float(terrain_config.get("load_attach_time", 5.0))
        self._load_attached = False
        self._load_body = None
        
        self._second_load_mass = float(terrain_config.get("second_load_mass", self.SECOND_LOAD_MASS))
        self._second_load_attach_time = float(terrain_config.get("second_load_attach_time", self.SECOND_LOAD_ATTACH_TIME))
        self._second_load_target_x = float(terrain_config.get("second_load_target_x", self.SECOND_LOAD_TARGET_X))
        self._second_load_attached = False
        self._second_load_body = None
        self._load2_dropped = False
        
        self._simulation_time = 0.0  # Track simulation time

    def step(self, time_step):
        """Physics step with load attachments"""
        # Update simulation time
        self._simulation_time += time_step
        current_time = self._simulation_time
        
        # Attach first load at t=5s to rightmost node (tip load)
        if not self._load_attached and current_time >= self._load_attach_time and self._bodies:
            rightmost_body = max(self._bodies, key=lambda b: b.position.x)
            rightmost_x = rightmost_body.position.x
            self._load_body = self._world.CreateDynamicBody(
                position=(rightmost_x, rightmost_body.position.y + 1.0),
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(0.5, 0.5)),
                    density=self._load_mass / (1.0 * 1.0),
                )
            )
            self._world.CreateWeldJoint(
                bodyA=rightmost_body,
                bodyB=self._load_body,
                anchor=(rightmost_x, rightmost_body.position.y),
                collideConnected=False
            )
            self._load_attached = True
            self._terrain_bodies["load"] = self._load_body

        # Second load logic: either dropped dynamically or welded to nearest node
        if self._drop_load:
            if not self._load2_dropped and current_time >= self._drop_time:
                self._second_load_body = self._world.CreateDynamicBody(
                    position=(self._drop_x, self._drop_y),
                    fixtures=Box2D.b2FixtureDef(
                        shape=polygonShape(box=(0.5, 0.5)),
                        density=self._drop_mass / (1.0 * 1.0),
                        friction=0.8,
                        restitution=0.1
                    )
                )
                self._load2_dropped = True
                self._second_load_attached = True # Mark as "attached" for evaluator timing logic
                self._terrain_bodies["load2"] = self._second_load_body
        else:
            # Attach second load at t=10s to mid-span node (body closest to target x in [5, 10])
            if not self._second_load_attached and current_time >= self._second_load_attach_time and self._bodies:
                candidates = [b for b in self._bodies if 5.0 <= b.position.x <= 10.0]
                if candidates:
                    mid_body = min(candidates, key=lambda b: abs(b.position.x - self._second_load_target_x))
                    mx, my = mid_body.position.x, mid_body.position.y
                    self._second_load_body = self._world.CreateDynamicBody(
                        position=(mx, my + 1.0),
                        fixtures=Box2D.b2FixtureDef(
                            shape=polygonShape(box=(0.5, 0.5)),
                            density=self._second_load_mass / (1.0 * 1.0),
                        )
                    )
                    self._world.CreateWeldJoint(
                        bodyA=mid_body,
                        bodyB=self._second_load_body,
                        anchor=(mx, my),
                        collideConnected=False
                    )
                    self._second_load_attached = True
                    self._terrain_bodies["load2"] = self._second_load_body
        
        self._world.Step(time_step, 10, 10)
        
        # Check joint torques (for anchor strength limit)
        for joint in self._wall_joints:
            if hasattr(joint, 'GetReactionTorque'):
                torque = abs(joint.GetReactionTorque(1.0/60.0))
                if torque > self._max_anchor_torque:
                    # Joint breaks - remove it
                    self._world.DestroyJoint(joint)
                    if joint in self._wall_joints:
                        self._wall_joints.remove(joint)
                    if joint in self._joints:
                        self._joints.remove(joint)

    # --- Physical constraint constants ---
    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 10.0
    MAX_BEAM_HEIGHT = 2.0  # Vertical extent of each beam limited (slender cantilever)
    WALL_X = 0.0
    MAX_ANCHOR_POINTS = 2  # Only 2 wall anchors; forces efficient truss
    MAX_ANCHOR_TORQUE = 2600.0  # Nm (tighter; naive cantilevers fail)
    TARGET_REACH = 14.0  # Must extend to at least x=14m
    MIN_TIP_HEIGHT = -2.5  # Tip must not sag below this y; stricter (e.g. -3.9m fails)  # Tip (or load) must not sag below this y; otherwise structure "failed" by excessive deflection
    LOAD_MASS = 600.0  # kg (tip load)
    SECOND_LOAD_MASS = 400.0  # kg (mid-span load)
    SECOND_LOAD_ATTACH_TIME = 10.0  # s
    SECOND_LOAD_TARGET_X = 7.5  # Attach to node nearest this x (mid-span)

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        """API: Add a beam"""
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_HEIGHT))
        
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
        """API: Add a joint (can anchor to wall)"""
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        
        # Check if anchoring to wall
        wall = self._terrain_bodies.get("wall")
        is_wall_anchor = (wall and (body_a == wall or body_b == wall))
        
        if is_wall_anchor:
            if len(self._wall_joints) >= self._max_anchor_points:
                raise ValueError(f"Maximum {self._max_anchor_points} anchor points on wall allowed")
            if self._forbidden_anchor_y is not None:
                ymin, ymax = self._forbidden_anchor_y
                if ymin <= anchor_y <= ymax:
                    raise ValueError(f"Anchor point y={anchor_y} is in the corrosive forbidden zone {self._forbidden_anchor_y}")
        
        if type == 'rigid':
            joint = self._world.CreateWeldJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=(anchor_x, anchor_y),
                collideConnected=False
            )
        elif type == 'pivot':
            joint = self._world.CreateRevoluteJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=(anchor_x, anchor_y),
                collideConnected=False
            )
        else:
            raise ValueError(f"Unknown joint type: {type}")
        
        self._joints.append(joint)
        if is_wall_anchor:
            self._wall_joints.append(joint)
        
        return joint

    def get_structure_mass(self):
        """API: Returns total mass"""
        total_mass = 0.0
        for body in self._bodies:
            total_mass += body.mass
        return total_mass

    def get_structure_reach(self):
        """Get maximum x position of structure"""
        if not self._bodies:
            return 0.0
        return max(b.position.x for b in self._bodies)

    def get_terrain_bounds(self):
        """Get terrain bounds (includes beam limits for consistency with prompt/feedback)."""
        return {
            "wall": {"x": self.WALL_X},
            "target_reach": self._target_reach,
            "max_anchor_points": self._max_anchor_points,
            "max_anchor_torque": self._max_anchor_torque,
            "load_mass": self._load_mass,
            "load_attach_time": self._load_attach_time,
            "second_load_mass": self._second_load_mass,
            "second_load_attach_time": self._second_load_attach_time,
            "second_load_target_x": self._second_load_target_x,
            "min_tip_height": float(self._terrain_config.get("min_tip_height", self.MIN_TIP_HEIGHT)),
            "max_beam_width": self.MAX_BEAM_SIZE,
            "max_beam_height": self.MAX_BEAM_HEIGHT,
            "obstacle_active": self._obstacle_active,
            "obstacle_rect": self._obstacle_rect if self._obstacle_active else None,
            "forbidden_anchor_y": self._forbidden_anchor_y,
        }
