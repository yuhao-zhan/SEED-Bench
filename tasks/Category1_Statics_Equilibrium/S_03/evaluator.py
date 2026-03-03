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
        
        # Prioritize environment's internal terrain config for mutations
        env_terrain_cfg = getattr(environment, "_terrain_config", {})
        self.target_reach = float(env_terrain_cfg.get("target_reach", terrain_bounds.get("target_reach", 12.0)))
        
        self.load_duration = 10.0 # seconds
        self.load_duration_steps = int(self.load_duration / TIME_STEP)
        
        # State tracking
        self.max_tip_x = 0.0
        self.initial_joint_count = 0
        self.structure_broken = False
        
        # Load phases (as defined in environment.py)
        self.load_attach_time = 5.0 # first load at 5s
        self.load_2_attach_time = 15.0 # second load at 15s
        self.load_attach_step = int(self.load_attach_time / TIME_STEP)
        self.load_2_attach_step = int(self.load_2_attach_time / TIME_STEP)
        
        # Design constraints
        if not environment:
            raise ValueError("Evaluator requires environment instance")
        
        # Take design limits from environment instance (allows mutation alignment)
        self.MAX_STRUCTURE_MASS = getattr(environment, 'MAX_STRUCTURE_MASS', 1500.0)
        self.BUILD_ZONE_X_MIN = getattr(environment, 'BUILD_ZONE_X_MIN', 0.0)
        self.BUILD_ZONE_X_MAX = getattr(environment, 'BUILD_ZONE_X_MAX', 35.0)
        self.BUILD_ZONE_Y_MIN = getattr(environment, 'BUILD_ZONE_Y_MIN', 0.0)
        self.BUILD_ZONE_Y_MAX = getattr(environment, 'BUILD_ZONE_Y_MAX', 15.0)
        
        self.design_constraints_checked = False
        self.reach_satisfied_initially = False

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        current_mass = self.environment.get_structure_mass()
        
        # Track max tip x during initial stable period (before first load)
        current_tip_x = self.environment.get_max_reach()
        if step_count < self.load_attach_step:
            self.max_tip_x = max(self.max_tip_x, current_tip_x)
            if self.max_tip_x >= self.target_reach:
                self.reach_satisfied_initially = True
        
        # Check structure integrity
        if step_count == 0:
            self.initial_joint_count = len(self.environment._joints)
        
        if len(self.environment._joints) < self.initial_joint_count:
            self.structure_broken = True
        
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
        
        # Reach check after initial stabilization
        if not failed and step_count >= self.load_attach_step + int(0.5/TIME_STEP):
            if current_tip_x < self.target_reach - 0.5: # Allow some sag under load
                failed, failure_reason = True, f"Structure sagged too much (tip x={current_tip_x:.2f}m < {self.target_reach-0.5}m)"

        # Determine success at end
        is_end = (step_count >= max_steps - 1)
        success = False
        
        if is_end and not failed:
            if not self.reach_satisfied_initially:
                failed, failure_reason = True, f"Structure never reached target x={self.target_reach}m"
            else:
                success = True
        
        done = failed or is_end
        score = 100.0 if success else 0.0
        if not done:
            score = min(current_tip_x / self.target_reach, 1.0) * 80.0
            
        metrics = {
            'tip_x': current_tip_x,
            'max_tip_x': self.max_tip_x,
            'target_reach': self.target_reach,
            'success': success,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'structure_mass': current_mass,
            'structure_broken': self.structure_broken,
        }
        
        return done, score, metrics

    def _check_design_constraints(self):
        violations = []
        if not self.environment: return ["Environment not available"]
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX and
                    self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX):
                violations.append(f"Beam at ({x:.2f}, {y:.2f}) outside build zone")
        return violations

    def get_task_description(self):
        return {
            'task': 'S-03: The Cantilever',
            'description': 'Design a structure that reaches far out and holds heavy loads',
            'success_criteria': {
                'reach': f'Tip x >= {self.target_reach}m',
                'load': 'Hold tip load and mid-span load for 10s each',
                'integrity': 'No joint or anchor breaks'
            }
        }
