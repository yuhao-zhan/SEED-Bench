"""
Control-Aware task environment module
Defines physics world, track, slider, API, etc.
Task: Speed-controlled slider that must dynamically adjust speed based on position
"""
import Box2D
from Box2D.b2 import (world, polygonShape, staticBody, dynamicBody, prismaticJoint)
import math


class DaVinciSandbox:
    """DaVinci Sandbox environment wrapper for speed-controlled slider task"""
    
    def __init__(self, *, terrain_config=None, physics_config=None):
        """
        Create a sandbox environment.
        """
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.0))

        # Initialize physics world
        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        
        # Track slider
        self._slider = None
        
        # For backward compatibility
        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints
        
        # Create track
        self._create_track(terrain_config)

    def _create_track(self, terrain_config: dict):
        """Create track"""
        track_friction = float(terrain_config.get("track_friction", 0.0))  # Frictionless
        
        # Create track (horizontal platform)
        track_y = 3.0
        track_length = 30.0
        track_width = 0.3
        
        self.track = self._world.CreateStaticBody(
            position=(track_length/2, track_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(track_length/2, track_width/2)),
                friction=float(track_friction),
            ),
        )

    # --- Physical constraint constants ---
    TRACK_Y = 3.0  # Track y position
    TRACK_START_X = 0.0
    TRACK_END_X = 30.0
    SLIDER_MAX_SPEED = 5.0  # m/s
    SLIDER_MIN_Y = 2.5  # Cannot fall below this
    SLIDER_MAX_Y = 3.5  # Cannot go above this
    
    # Speed limit zones
    SPEED_ZONE_1_START = 0.0
    SPEED_ZONE_1_END = 10.0
    SPEED_ZONE_1_LIMIT = 1.5  # m/s
    
    SPEED_ZONE_2_START = 10.0
    SPEED_ZONE_2_END = 20.0
    SPEED_ZONE_2_LIMIT = 3.0  # m/s
    
    SPEED_ZONE_3_START = 20.0
    SPEED_ZONE_3_END = 30.0
    SPEED_ZONE_3_LIMIT = 2.0  # m/s

    # --- Primitives API ---

    def add_slider(self, x, y, width, height, density=1.0):
        """
        API: Add a slider on the track
        Slider is constrained to move horizontally along the track
        """
        # Place slider on top of track (not overlapping with track center)
        # Track center is at TRACK_Y, track height is 0.3m (track_width)
        # Slider should be placed so its bottom edge is on top of track
        track_width = 0.3
        slider_y = self.TRACK_Y + track_width/2 + height/2
        
        body = self._world.CreateDynamicBody(
            position=(x, slider_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(width/2, height/2)),
                density=density,
                friction=0.0,  # Frictionless
            )
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        body.fixedRotation = True  # Slider doesn't rotate
        
        # Don't use prismatic joint - it's too restrictive
        # Instead, just constrain y position manually in step()
        # Slider can move freely in x direction
        
        self._bodies.append(body)
        self._slider = body
        
        return body

    def get_slider_state(self, slider):
        """
        Get slider state: position and velocity
        Returns: (position_x, velocity_x)
        """
        if not slider:
            return 0.0, 0.0
        
        pos = slider.position
        vel = slider.linearVelocity
        
        return pos.x, vel.x

    def set_slider_velocity(self, slider, velocity_x):
        """
        Set slider horizontal velocity
        """
        if not slider:
            return
        
        # Clamp velocity (non-negative, max speed)
        velocity_x = max(0.0, min(self.SLIDER_MAX_SPEED, velocity_x))
        
        # Set velocity directly
        # Store in a custom attribute so we can restore it after physics step
        slider._target_velocity_x = velocity_x
        slider.linearVelocity = (velocity_x, 0.0)

    def apply_force_to_slider(self, slider, force_x):
        """
        Apply horizontal force to slider
        """
        if not slider:
            return
        
        # Clamp force (only positive - forward direction)
        max_force = slider.mass * 50.0  # Max acceleration
        force_x = max(0.0, min(max_force, force_x))
        
        # Apply force at center
        slider.ApplyForce((force_x, 0), slider.position, True)

    def step(self, time_step):
        """Physics step"""
        # Set target velocity BEFORE physics step to ensure it's applied
        if self._slider:
            if hasattr(self._slider, '_target_velocity_x'):
                target_vel_x = self._slider._target_velocity_x
                self._slider.linearVelocity = (target_vel_x, 0.0)
            else:
                # If no target velocity set, just zero y velocity
                vel = self._slider.linearVelocity
                self._slider.linearVelocity = (vel.x, 0.0)
        
        # Physics step
        self._world.Step(time_step, 10, 10)
        
        # Constrain slider to track and restore target velocity after physics step
        if self._slider:
            pos = self._slider.position
            # Force slider to stay on track (only fix y position, preserve x)
            # Slider should be on top of track (track_y + track_width/2 + slider_height/2)
            track_width = 0.3
            slider_height = 0.3  # From agent.py: height=0.3
            target_y = self.TRACK_Y + track_width/2 + slider_height/2
            if abs(pos.y - target_y) > 0.01:
                self._slider.position = (pos.x, target_y)  # Preserve x position
            
            # Restore target velocity after physics step (collision may have changed it)
            if hasattr(self._slider, '_target_velocity_x'):
                target_vel_x = self._slider._target_velocity_x
                self._slider.linearVelocity = (target_vel_x, 0.0)
            else:
                # If no target velocity set, just zero y velocity
                vel = self._slider.linearVelocity
                self._slider.linearVelocity = (vel.x, 0.0)
    
    def get_terrain_bounds(self):
        """Get terrain bounds (for evaluation)"""
        return {
            "track_start": self.TRACK_START_X,
            "track_end": self.TRACK_END_X,
            "track_y": self.TRACK_Y,
        }
    
    def get_speed_zone_limits(self):
        """Get speed zone limits (for evaluator)"""
        return {
            "zone_1": {
                "start": self.SPEED_ZONE_1_START,
                "end": self.SPEED_ZONE_1_END,
                "limit": self.SPEED_ZONE_1_LIMIT
            },
            "zone_2": {
                "start": self.SPEED_ZONE_2_START,
                "end": self.SPEED_ZONE_2_END,
                "limit": self.SPEED_ZONE_2_LIMIT
            },
            "zone_3": {
                "start": self.SPEED_ZONE_3_START,
                "end": self.SPEED_ZONE_3_END,
                "limit": self.SPEED_ZONE_3_LIMIT
            }
        }
