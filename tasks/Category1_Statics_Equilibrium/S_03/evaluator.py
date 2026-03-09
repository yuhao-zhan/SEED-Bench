"""
S-03: The Cantilever task evaluation module
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation system for S-03: The Cantilever
    Success: tip reaches target x, stays intact under two sequential heavy loads.
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        if not environment:
            raise ValueError("Evaluator requires environment instance")
            
        # Prioritize environment's internal terrain config for mutations
        env_terrain_cfg = getattr(environment, "_terrain_config", {})
        self.target_reach = float(env_terrain_cfg.get("target_reach", 12.0))
        
        self.load_duration = 10.0 # seconds
        self.load_duration_steps = int(self.load_duration / TIME_STEP)
        
        # State tracking
        self.max_tip_x = 0.0
        self.min_tip_y = 1e9
        self.min_tip_height_limit = -15.0 # Allowed sag limit in world Y
        
        self.initial_joint_count = -1
        self.structure_broken = False
        
        # Load phases (aligned with environment.py)
        self.load_attach_time = 5.0 # first load at 5s
        self.load_2_attach_time = 15.0 # second load at 15s
        self.load_attach_step = int(self.load_attach_time / TIME_STEP)
        self.load_2_attach_step = int(self.load_2_attach_time / TIME_STEP)
        
        self.load_1_held_steps = 0
        self.load_2_held_steps = 0
        self.last_step_count = 0
        
        # Take design limits from environment instance
        self.MAX_STRUCTURE_MASS = getattr(environment, 'MAX_STRUCTURE_MASS', 15000.0)
        self.BUILD_ZONE_X_MIN = getattr(environment, 'BUILD_ZONE_X_MIN', 0.0)
        self.BUILD_ZONE_X_MAX = getattr(environment, 'BUILD_ZONE_X_MAX', 50.0)
        self.BUILD_ZONE_Y_MIN = getattr(environment, 'BUILD_ZONE_Y_MIN', -20.0)
        self.BUILD_ZONE_Y_MAX = getattr(environment, 'BUILD_ZONE_Y_MAX', 30.0)
        
        self.max_recorded_torque = 0.0
        self.torque_limit_recorded = 0.0
        self.external_force_y = 0.0
        
        self.design_constraints_checked = False
        self.reach_satisfied_initially = False

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        current_mass = self.environment.get_structure_mass()
        current_tip_x = self.environment.get_max_reach()
        
        # Initialize joint count once
        if self.initial_joint_count == -1:
            self.initial_joint_count = len(self.environment._joints)

        # Track max reach and min height
        self.max_tip_x = max(self.max_tip_x, current_tip_x)
        if step_count < self.load_attach_step:
            if self.max_tip_x >= self.target_reach:
                self.reach_satisfied_initially = True
        
        # Track min tip height across all structure bodies
        total_ext_force_y = 0.0
        for body in self.environment._bodies:
            self.min_tip_y = min(self.min_tip_y, body.position.y)
            
            # Sum up external forces for discovery feedback
            # Spatial force
            spatial_force = self.environment._physics_config.get("spatial_force", None)
            if spatial_force:
                cx, cy = spatial_force.get("center", (0,0))
                mag = spatial_force.get("magnitude", 0.0)
                radius = spatial_force.get("radius", 10.0)
                is_repulsion = spatial_force.get("type", "repulsion") == "repulsion"
                bx, by = body.position
                dx, dy = bx - cx, by - cy
                dist = math.sqrt(dx**2 + dy**2)
                if dist < radius and dist > 0.1:
                    f = mag * (1.0 - dist / radius)
                    if not is_repulsion: f = -f
                    fy = f * (dy / dist)
                    total_ext_force_y += fy
            
            # Wind force
            wind_config = self.environment._physics_config.get("wind", None)
            if wind_config:
                force_vec = wind_config.get("force", (0, 0))
                if wind_config.get("oscillatory", False):
                    freq = wind_config.get("frequency", 1.0)
                    phase = math.sin(self.environment._simulation_time * 2 * math.pi * freq)
                    force_vec = (force_vec[0] * phase, force_vec[1] * phase)
                total_ext_force_y += force_vec[1]

        self.external_force_y = total_ext_force_y / len(self.environment._bodies) if self.environment._bodies else 0.0

        # Record max torque usage (using fixed 60Hz frequency for consistency)
        for joint in self.environment._joints:
            try:
                force = joint.GetReactionForce(60.0)
                torque = abs(joint.GetReactionTorque(60.0))
                self.max_recorded_torque = max(self.max_recorded_torque, torque)
            except: pass
            
        # Determine current torque limit (simplified to max found in config)
        self.torque_limit_recorded = self.environment._terrain_config.get("max_anchor_torque", 100000000.0)


        # Structural integrity check
        if len(self.environment._joints) < self.initial_joint_count:
            self.structure_broken = True
        
        # Advanced hold tracking: calculate delta steps since last call
        steps_delta = step_count - self.last_step_count
        if not self.structure_broken:
            # Increment hold steps if we are within/past the load phase
            if step_count >= self.load_attach_step:
                # Add elapsed steps that fall within the payload-active period
                active_steps = max(0, step_count - max(self.last_step_count, self.load_attach_step))
                self.load_1_held_steps += active_steps
            if step_count >= self.load_2_attach_step:
                active_steps = max(0, step_count - max(self.last_step_count, self.load_2_attach_step))
                self.load_2_held_steps += active_steps
        
        self.last_step_count = step_count

        failed = False
        failure_reason = None
        
        # Continuous mass check
        if current_mass > self.MAX_STRUCTURE_MASS:
            failed, failure_reason = True, f"Structure mass {current_mass:.2f}kg exceeds maximum {self.MAX_STRUCTURE_MASS}kg"
            
        if not failed and not self.design_constraints_checked and step_count == 0:
            violations = self._check_design_constraints()
            if violations:
                failed, failure_reason = True, "Design constraint violated: " + "; ".join(violations)
            self.design_constraints_checked = True
        
        # Failure: structure broke
        if not failed and self.structure_broken:
            failed, failure_reason = True, "Structure integrity lost (joints or wall anchors broke)"
        
        # Failure: sagged too much
        if not failed and self.min_tip_y < self.min_tip_height_limit:
            failed, failure_reason = True, f"Structure sagged too much (tip y={self.min_tip_y:.2f}m < {self.min_tip_height_limit}m)"

        # Failure: lost reach during test
        if not failed and step_count >= self.load_attach_step:
            if current_tip_x < self.target_reach - 1.0: # Tolerance for deflection
                failed, failure_reason = True, f"Structure lost reach under load (tip x={current_tip_x:.2f}m < {self.target_reach-1.0}m)"

        # Final determination
        is_end = (step_count >= max_steps - 1)
        success = False
        
        if is_end and not failed:
            if not self.reach_satisfied_initially:
                failed, failure_reason = True, f"Structure never reached target x={self.target_reach}m"
            elif self.load_1_held_steps < self.load_duration_steps:
                 failed, failure_reason = True, f"Failed to hold first load for required duration (held {self.load_1_held_steps * TIME_STEP:.2f}s / {self.load_duration}s)"
            elif self.load_2_held_steps < self.load_duration_steps:
                 failed, failure_reason = True, f"Failed to hold second load for required duration (held {self.load_2_held_steps * TIME_STEP:.2f}s / {self.load_duration}s)"
            else:
                success = True
        
        done = failed or (is_end and success) or (is_end and not success)
        
        score = 100.0 if success else 0.0
        if not done:
            score = min(current_tip_x / self.target_reach, 1.0) * 80.0
            
        metrics = {
            'tip_x': current_tip_x,
            'max_reach': self.max_tip_x,
            'target_reach': self.target_reach,
            'current_reach': current_tip_x,
            'load_attached': step_count >= self.load_attach_step,
            'load_hold_time': self.load_1_held_steps * TIME_STEP,
            'load2_attached': step_count >= self.load_2_attach_step,
            'load2_hold_time': self.load_2_held_steps * TIME_STEP,
            'anchor_broken': self.structure_broken,
            'min_tip_y': self.min_tip_y,
            'min_tip_height': self.min_tip_height_limit,
            'tip_sagged': self.min_tip_y < self.min_tip_height_limit,
            'external_force_y': self.external_force_y,
            'structure_mass': current_mass,
            'max_structure_mass': self.MAX_STRUCTURE_MASS,
            'max_anchor_torque': self.max_recorded_torque,
            'max_anchor_torque_limit': self.torque_limit_recorded,
            'anchor_count': len([j for j in self.environment._joints if j.bodyA == self.environment._terrain_bodies["wall"] or j.bodyB == self.environment._terrain_bodies["wall"]]),
            'max_anchor_points': 2,
            'joint_count': len(self.environment._joints),
            'initial_joint_count': self.initial_joint_count,
            'success': success,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
        }
        
        return done, score, metrics

    def _check_design_constraints(self):
        violations = []
        if not self.environment: return ["Environment not available"]
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (self.BUILD_ZONE_X_MIN - 5.0 <= x <= self.BUILD_ZONE_X_MAX + 5.0 and
                    self.BUILD_ZONE_Y_MIN - 5.0 <= y <= self.BUILD_ZONE_Y_MAX + 5.0):
                violations.append(f"Beam at ({x:.2f}, {y:.2f}) outside build zone")
        
        anchor_count = len([j for j in self.environment._joints if j.bodyA == self.environment._terrain_bodies["wall"] or j.bodyB == self.environment._terrain_bodies["wall"]])
        if anchor_count > 2:
            violations.append(f"Too many wall anchors: {anchor_count} (max 2)")
            
        return violations

    def get_task_description(self):
        return {
            'task': 'S-03: The Cantilever',
            'description': 'Design a structure that reaches far out and holds heavy loads',
            'success_criteria': {
                'reach': f'Tip x >= {self.target_reach}m',
                'load': 'Hold all payloads for 10s duration',
                'integrity': 'No joint or anchor breaks'
            }
        }
