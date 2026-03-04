"""
S-04: The Balancer task evaluation module
"""
import math


class Evaluator:
    """Evaluation system for S-04: The Balancer"""
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.max_angle_deviation = 10.0 * math.pi / 180.0
        self.balance_time = 15.0  # Will be overridden below if environment provides it
        
        self.load_caught = False
        self.balance_start_time = None
        self.balance_duration = 0.0
        self.max_angle_seen = 0.0
        
        if not environment:
            raise ValueError("Evaluator requires environment instance")
        
        env_class = type(environment)
        try:
            # Read from instance attributes first (for mutated tasks), fallback to class constants
            self.MAX_ANGLE_DEVIATION = getattr(environment, 'MAX_ANGLE_DEVIATION', env_class.MAX_ANGLE_DEVIATION)
            self.BALANCE_TIME = getattr(environment, 'BALANCE_TIME', env_class.BALANCE_TIME)
            # Also update balance_time (used in evaluate method)
            self.balance_time = self.BALANCE_TIME
            self.max_angle_deviation = self.MAX_ANGLE_DEVIATION
        except AttributeError as e:
            raise AttributeError(f"Environment class {env_class.__name__} missing required constant: {e}")
        
        self.design_constraints_checked = False
        
    def evaluate(self, agent_body, step_count, max_steps):
        """Evaluate balancer performance"""
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        # Check if load is caught
        if "load" in self.environment._terrain_bodies:
            self.load_caught = True
        
        # Get main beam angle
        beam_angle = self.environment.get_main_beam_angle()
        angle_deviation = abs(beam_angle)
        self.max_angle_seen = max(self.max_angle_seen, angle_deviation)
        
        # Track balance duration
        time_step = 1.0 / 60.0
        current_time = step_count * time_step
        
        if angle_deviation <= self.max_angle_deviation:
            if self.balance_start_time is None:
                self.balance_start_time = current_time
            self.balance_duration = current_time - self.balance_start_time
        else:
            self.balance_start_time = None
            self.balance_duration = 0.0
        
        # Check success
        catch_ok = self.load_caught
        balance_ok = self.balance_duration >= self.balance_time
        
        success = catch_ok and balance_ok
        
        # Check failures
        failed = False
        failure_reason = None
        
        # Check if load touches ground
        load_body = self.environment._terrain_bodies.get("load")
        if load_body and load_body.position.y < -0.1:
            failed = True
            failure_reason = f"Load fell to the ground (y={load_body.position.y:.2f} < -0.1)"
        
        # Check if any body touches ground
        for i, body in enumerate(self.environment._bodies):
            if body.position.y < -0.1:
                failed = True
                failure_reason = f"Structure body {i} touched ground (y={body.position.y:.2f} < -0.1)"
                break
        
        # Fail fast only for hard-constraint violations:
        # - load not caught early
        # - structure touches ground
        # - angle blows past limit (large tilt), not merely "not yet balanced for 15s"
        if not catch_ok and current_time > 1.0:
            failed = True
            failure_reason = "Failed to catch load at (3,0)"
        elif catch_ok and angle_deviation > self.max_angle_deviation and current_time > 2.0:
            failed = True
            failure_reason = f"Beam angle {angle_deviation * 180 / math.pi:.1f}° exceeds ±10° limit"
        
        # Calculate score
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            catch_score = 50.0 if catch_ok else 0.0
            balance_score = min(self.balance_duration / self.balance_time, 1.0) * 50.0
            score = catch_score + balance_score
        
        # --- richer physical metrics (for feedback/debug) ---
        structure_mass = 0.0
        com_x = 0.0
        com_y = 0.0
        min_body_y = None
        
        # Calculate net static torque precisely
        net_torque_about_pivot = 0.0
        gx, gy = getattr(self.environment.world, "gravity", (0.0, -10.0)) if self.environment else (0.0, -10.0)
        wind_f = float(getattr(self.environment, "_wind_force_multiplier", 0.0)) if getattr(self.environment, "_wind_active", False) else 0.0

        for body in getattr(self.environment, "_bodies", []):
            m = float(getattr(body, "mass", 0.0))
            structure_mass += m
            rx, ry = float(body.position.x), float(body.position.y)
            com_x += m * rx
            com_y += m * ry
            min_body_y = ry if min_body_y is None else min(min_body_y, ry)
            
            Fx = m * wind_f + m * gx
            Fy = m * gy
            net_torque_about_pivot += (rx * Fy - ry * Fx)

        if structure_mass > 1e-9:
            com_x /= structure_mass
            com_y /= structure_mass
        else:
            com_x, com_y = 0.0, 0.0

        load_body = getattr(self.environment, "_terrain_bodies", {}).get("load")
        load_mass = None
        load_pos = None
        if load_body is not None:
            load_mass = float(getattr(load_body, "mass", 0.0))
            rx, ry = float(load_body.position.x), float(load_body.position.y)
            load_pos = (rx, ry)
            
            # Include load in the torque if it's attached or interacting
            if getattr(self.environment, "_load_attached", False) or getattr(self.environment, "_drop_load", False):
                Fx = load_mass * wind_f + load_mass * gx
                Fy = load_mass * gy
                net_torque_about_pivot += (rx * Fy - ry * Fx)

        metrics = {
            'load_caught': self.load_caught,
            'beam_angle_deg': beam_angle * 180 / math.pi,
            'max_angle_seen_deg': self.max_angle_seen * 180 / math.pi,
            'balance_duration': self.balance_duration,
            'target_balance_time': self.balance_time,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            # extra metrics for debugging / physics insight
            'structure_mass': structure_mass,
            'structure_com_x': com_x,
            'structure_com_y': com_y,
            'min_body_y': min_body_y,
            'net_torque_about_pivot': net_torque_about_pivot,
            'load_mass': load_mass,
            'load_pos': load_pos,
        }
        
        return success or failed, score, metrics
    
    def _check_design_constraints(self):
        """Check design constraints"""
        return []
    
    def get_task_description(self):
        """Return task description"""
        return {
            'task': 'S-04: The Balancer',
            'description': 'Build a structure that balances on a pivot',
            'success_criteria': {
                'catch': 'Connect to load at (3,0)',
                'balance': f'Keep angle within ±10° for {self.balance_time}s'
            }
        }
