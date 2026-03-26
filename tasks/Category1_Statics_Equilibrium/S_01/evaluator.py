"""
S-01: The Bridge task evaluation module
Defines task objectives and success criteria
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation system: Defines task objectives and success criteria for S-01: The Bridge
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        # Determine target x: right cliff start + 5m
        gap_info = terrain_bounds.get("gap", {})
        right_cliff_start = gap_info.get("x_end", 25.0)
        self.target_x = right_cliff_start + 5.0
        
        # Cliff top and stall threshold from terrain (not hardcoded)
        left_cliff = terrain_bounds.get("left_cliff", {})
        self._cliff_top_y = float(left_cliff.get("y", 10.0))
        gap_x_start = float(gap_info.get("x_start", 10.0))
        gap_width = float(gap_info.get("width", 15.0))
        self.stall_threshold_x = gap_x_start + gap_width / 3.0
        
        # Baseline gravity is 10.0 m/s^2; use actual world gravity for mutations (3.0g)
        gravity_mag = abs(environment._world.gravity.y) if environment and hasattr(environment._world, 'gravity') else 10.0
        self.max_vertical_acceleration = 3.0 * gravity_mag
        
        # Stability tracking
        self.high_angular_velocity_count = 0
        self.MAX_ANGULAR_VELOCITY = 2.0
        self.STABILITY_CHECK_START_STEP = 200
        self.UNSTABLE_THRESHOLD = 5
        
        # Air rotation tracking
        self.MAX_AIRBORNE_ROTATION = math.pi
        self.AIRBORNE_THRESHOLD = 1.5
        self._rotation_tracking_initialized = False
        
        # Track vehicle state
        self.vehicle_previous_velocity_y = 0.0
        self._last_eval_step_count = 0
        self.max_vertical_accel_seen = 0.0
        self.failure_detected_step = -1
        
        # Track structure integrity
        self.initial_joint_count = 0
        self.structure_broken = False
        
        # Design constraints from environment instance or class
        if not environment:
            raise ValueError("Evaluator requires environment instance")
        
        env_class = type(environment)
        self.MAX_STRUCTURE_MASS = getattr(environment, 'MAX_STRUCTURE_MASS', getattr(env_class, 'MAX_STRUCTURE_MASS', 2000.0))
        self.BUILD_ZONE_X_MIN = getattr(environment, 'BUILD_ZONE_X_MIN', getattr(env_class, 'BUILD_ZONE_X_MIN', 10.0))
        self.BUILD_ZONE_X_MAX = getattr(environment, 'BUILD_ZONE_X_MAX', getattr(env_class, 'BUILD_ZONE_X_MAX', 30.0))
        self.BUILD_ZONE_Y_MIN = getattr(environment, 'BUILD_ZONE_Y_MIN', getattr(env_class, 'BUILD_ZONE_Y_MIN', 5.0))
        self.BUILD_ZONE_Y_MAX = getattr(environment, 'BUILD_ZONE_Y_MAX', getattr(env_class, 'BUILD_ZONE_Y_MAX', 15.0))
        self.MIN_DECK_FRICTION = getattr(environment, 'MIN_DECK_FRICTION', getattr(env_class, 'MIN_DECK_FRICTION', 0.5))
        self.MIN_BEAM_SIZE = getattr(environment, 'MIN_BEAM_SIZE', getattr(env_class, 'MIN_BEAM_SIZE', 0.1))
        self.MAX_BEAM_SIZE = getattr(environment, 'MAX_BEAM_SIZE', getattr(env_class, 'MAX_BEAM_SIZE', 10.0))
        
        # Fail zone: source from environment so evaluation stays aligned if fail_zone_y is ever configurable
        bounds = getattr(environment, 'get_terrain_bounds', lambda: {})()
        self.fail_zone_y = float(bounds.get("fail_zone_y", 0.5))
        
        self.design_constraints_checked = False
        
    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        vehicle_pos = self.environment.get_vehicle_position()
        vehicle_vel = self.environment.get_vehicle_velocity()
        
        if vehicle_pos is None or vehicle_vel is None:
            return False, 0.0, {"error": "Vehicle not found"}
        
        current_x, current_y = vehicle_pos
        velocity_x, velocity_y = vehicle_vel
        
        vehicle_chassis = self.environment._terrain_bodies.get("vehicle_chassis")
        angular_velocity = vehicle_chassis.angularVelocity if vehicle_chassis else 0.0
        angle = vehicle_chassis.angle if vehicle_chassis else 0.0
        
        # Acceleration from velocity change: use actual step delta since last evaluation
        steps_delta = step_count - self._last_eval_step_count
        actual_time_step = steps_delta * TIME_STEP if steps_delta > 0 else TIME_STEP
        if step_count > 0 and steps_delta > 0:
            vertical_accel = abs(velocity_y - self.vehicle_previous_velocity_y) / actual_time_step
            self.max_vertical_accel_seen = max(self.max_vertical_accel_seen, vertical_accel)
        self._last_eval_step_count = step_count
        self.vehicle_previous_velocity_y = velocity_y
        
        if step_count == 0:
            self.initial_joint_count = len(self.environment._joints)
        
        if len(self.environment._joints) < self.initial_joint_count:
            self.structure_broken = True
        
        success = current_x >= self.target_x
        failed = False
        failure_reason = None
        
        if not self.design_constraints_checked and step_count == 0:
            violations = self._check_design_constraints()
            if violations:
                failed, failure_reason = True, "Design constraint violated: " + "; ".join(violations)
                if self.failure_detected_step == -1: self.failure_detected_step = step_count
            self.design_constraints_checked = True
        
        # Fail check: any dynamic body (vehicle or structure) must stay above fail_zone_y
        if not failed:
            # Check vehicle chassis and wheels (from terrain bodies)
            for body_name in ["vehicle_chassis", "vehicle_wheel1", "vehicle_wheel2"]:
                body = self.environment._terrain_bodies.get(body_name)
                if body:
                    min_y = body.position.y
                    for fixture in body.fixtures:
                        shape = fixture.shape
                        if hasattr(shape, 'radius') and not hasattr(shape, 'vertices'): # Circle
                            min_y = min(min_y, body.position.y - shape.radius)
                        elif hasattr(shape, 'vertices'): # Polygon
                            for v in shape.vertices:
                                world_v = body.GetWorldPoint(v)
                                min_y = min(min_y, world_v.y)
                    
                    if min_y <= self.fail_zone_y:
                        failed = True
                        failure_reason = f"Vehicle component {body_name} fell into fail zone (y={min_y:.2f} <= {self.fail_zone_y})"
                        if self.failure_detected_step == -1: self.failure_detected_step = step_count
                        break

            # Check structure beams
            if not failed:
                for body in self.environment._bodies:
                    min_y = body.position.y
                    for fixture in body.fixtures:
                        shape = fixture.shape
                        if hasattr(shape, 'vertices'):
                            for v in shape.vertices:
                                world_v = body.GetWorldPoint(v)
                                min_y = min(min_y, world_v.y)
                    
                    if min_y <= self.fail_zone_y:
                        failed = True
                        failure_reason = f"Structural component entered fail zone (y={min_y:.2f} <= {self.fail_zone_y} m)"
                        if self.failure_detected_step == -1: self.failure_detected_step = step_count
                        break

        if not failed and self.structure_broken:
            failed, failure_reason = True, "Structure integrity lost (joints broke)"
            if self.failure_detected_step == -1: self.failure_detected_step = self.environment.joint_break_events[0]['step'] if self.environment.joint_break_events else step_count
        
        if not failed and self.max_vertical_accel_seen > self.max_vertical_acceleration:
            # Report in g to hide the absolute gravity value.
            accel_g = (self.max_vertical_accel_seen / self.max_vertical_acceleration) * 3.0
            failed, failure_reason = True, f"Vehicle vertical acceleration {accel_g:.2f}g exceeds the 3.0g limit"
            if self.failure_detected_step == -1: self.failure_detected_step = step_count
        
        if not failed and step_count > self.STABILITY_CHECK_START_STEP:
            if abs(angular_velocity) >= self.MAX_ANGULAR_VELOCITY:
                self.high_angular_velocity_count += 1
                if self.high_angular_velocity_count >= self.UNSTABLE_THRESHOLD:
                    failed, failure_reason = True, f"Vehicle unstable (angular velocity {angular_velocity:.2f} rad/s)"
                    if self.failure_detected_step == -1: self.failure_detected_step = step_count
            else:
                self.high_angular_velocity_count = 0
        
        normalized_angle = (angle + math.pi) % (2 * math.pi) - math.pi
        if not failed and abs(normalized_angle) > math.pi / 2:
            failed, failure_reason = True, f"Vehicle flipped ({math.degrees(abs(normalized_angle)):.1f}°)"
            if self.failure_detected_step == -1: self.failure_detected_step = step_count

        if not self._rotation_tracking_initialized and self.environment and vehicle_chassis:
            if hasattr(self.environment, 'set_tracked_body'):
                self.environment.set_tracked_body(vehicle_chassis)
                self._rotation_tracking_initialized = True
        
        airborne_rotation_accumulated = 0.0
        if not failed and self.environment and hasattr(self.environment, 'get_airborne_rotation_status'):
            rotation_status = self.environment.get_airborne_rotation_status()
            airborne_rotation_accumulated = rotation_status['accumulated']
            if rotation_status['exceeded']:
                failed, failure_reason = True, f"Vehicle rotated {math.degrees(airborne_rotation_accumulated):.1f}° while airborne"
                if self.failure_detected_step == -1: self.failure_detected_step = step_count

        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            start_x = 5.0
            max_dist = self.target_x - start_x
            progress = min(max(0, current_x - start_x) / max_dist, 1.0) if max_dist > 0 else 0.0
            score = progress * 80.0
        
        metrics = {
            'vehicle_x': current_x, 'vehicle_y': current_y, 'target_x': self.target_x,
            'velocity_x': velocity_x, 'velocity_y': velocity_y,
            'angular_velocity': angular_velocity, 'angle': angle, 'normalized_angle': normalized_angle,
            'max_vertical_accel': self.max_vertical_accel_seen,
            'max_vertical_acceleration_limit': self.max_vertical_acceleration,
            'vehicle_start_x': 5.0,
            'max_airborne_rotation_limit': self.MAX_AIRBORNE_ROTATION,
            'stall_threshold_x': self.stall_threshold_x,
            'fail_zone_y': self.fail_zone_y,
            'success': success and not failed, 'failed': failed, 'failure_reason': failure_reason,
            'step_count': step_count, 'structure_mass': self.environment.get_structure_mass(),
            'max_joint_force': self.environment.get_max_joint_stress()[0], 'max_joint_torque': self.environment.get_max_joint_stress()[1],
            'max_structure_mass': self.MAX_STRUCTURE_MASS, 'structure_broken': self.structure_broken,
            'joint_count': len(self.environment._joints), 'initial_joint_count': self.initial_joint_count,
            'is_airborne': current_y > (self._cliff_top_y + self.AIRBORNE_THRESHOLD),
            'airborne_rotation_accumulated': airborne_rotation_accumulated,
            'high_angular_velocity_count': self.high_angular_velocity_count,
            'failure_step': self.failure_detected_step,
            'joint_break_events': self.environment.joint_break_events,
        }
        return success or failed, score, metrics
    
    def _check_design_constraints(self):
        violations = []
        if not self.environment: return ["Environment not available"]
        mass = self.environment.get_structure_mass()
        if mass >= self.MAX_STRUCTURE_MASS:
            violations.append(f"Mass {mass:.2f}kg exceeds maximum {self.MAX_STRUCTURE_MASS}kg")
        
        # Build zone: allow extension to target for deck
        build_zone_x_max = max(self.BUILD_ZONE_X_MAX, self.target_x)
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (self.BUILD_ZONE_X_MIN <= x <= build_zone_x_max and
                    self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX):
                violations.append(f"Beam at ({x:.2f}, {y:.2f}) outside build zone")
            
            # Beam dimensions: check if any fixture shape exceeds bounds
            for fixture in body.fixtures:
                shape = fixture.shape
                if hasattr(shape, 'vertices'):
                    # Polygon box extents
                    xs = [v[0] for v in shape.vertices]
                    ys = [v[1] for v in shape.vertices]
                    width = max(xs) - min(xs)
                    height = max(ys) - min(ys)
                    if not (self.MIN_BEAM_SIZE - 1e-4 <= width <= self.MAX_BEAM_SIZE + 1e-4 and
                            self.MIN_BEAM_SIZE - 1e-4 <= height <= self.MAX_BEAM_SIZE + 1e-4):
                        violations.append(f"Beam at ({x:.2f}, {y:.2f}) dimensions {width:.2f}x{height:.2f} exceed allowed [{self.MIN_BEAM_SIZE}, {self.MAX_BEAM_SIZE}]")
                
                # Traction: each beam (deck surface) must have friction >= MIN_DECK_FRICTION
                if getattr(fixture, 'friction', 0) < self.MIN_DECK_FRICTION:
                    violations.append(
                        f"Beam at ({x:.2f}, {y:.2f}) has friction {getattr(fixture, 'friction', 0):.2f} "
                        f"below minimum {self.MIN_DECK_FRICTION}"
                    )
                    break
        return violations
    
    def get_task_description(self):
        return {
            'task': 'S-01: The Bridge',
            'description': 'Design a bridge to connect two cliffs and support a testing vehicle',
            'target_position': self.target_x,
            'success_criteria': {
                'primary': f'Vehicle reaches x={self.target_x}m',
                'secondary': 'No structural breaks',
                'tertiary': 'Acceleration < 3g',
            },
            'evaluation': {'score_range': '0-100', 'success_score': 100, 'failure_score': 0}
        }
