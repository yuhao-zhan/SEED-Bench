"""
S-05: The Shelter task evaluation module
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """Evaluator for S-05: The Shelter task"""

    def __init__(self, terrain_bounds, environment=None):
        self.environment = environment
        self.terrain_bounds = terrain_bounds
        self.max_core_force = float(self.terrain_bounds.get("core_max_force", 150.0))
        self.MAX_STRUCTURE_HEIGHT = float(self.terrain_bounds.get("max_structure_height", 7.5))
        # Minimum steps to evaluate success: at least cover full bombardment when terrain_bounds provide it
        meteor_count = int(self.terrain_bounds.get("meteor_count", 12))
        meteor_spawn_interval = int(self.terrain_bounds.get("meteor_spawn_interval", 30))
        self.min_steps = max(1000, meteor_count * meteor_spawn_interval)
        # Build zone from environment for consistency (e.g. design-constraint checks)
        env_class = type(environment) if environment else None
        self.BUILD_ZONE_X_MIN = getattr(environment, 'BUILD_ZONE_X_MIN', getattr(env_class, 'BUILD_ZONE_X_MIN', 5.0)) if environment else 5.0
        self.BUILD_ZONE_X_MAX = getattr(environment, 'BUILD_ZONE_X_MAX', getattr(env_class, 'BUILD_ZONE_X_MAX', 15.0)) if environment else 15.0
        self.BUILD_ZONE_Y_MIN = getattr(environment, 'BUILD_ZONE_Y_MIN', getattr(env_class, 'BUILD_ZONE_Y_MIN', 0.0)) if environment else 0.0
        self.BUILD_ZONE_Y_MAX = getattr(environment, 'BUILD_ZONE_Y_MAX', getattr(env_class, 'BUILD_ZONE_Y_MAX', 8.0)) if environment else 8.0

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        core_force = self.environment.get_core_max_force()
        structure_mass = self.environment.get_structure_mass()
        max_mass = float(self.terrain_bounds.get("max_structure_mass", 300.0))
        
        failed = False
        failure_reason = None
        
        # Design constraint check (collapse)
        # The core default is at y=1.0 (may differ in mutated stages). If structure falls below 0.3, it's definitely a collapse.
        min_body_y = 100.0
        if self.environment._bodies:
            for body in self.environment._bodies:
                min_body_y = min(min_body_y, body.position.y)
        
        # Joint limit check: if this environment has restrictive joint limits and we observed peak force/torque above them, treat as structural failure (joint would have broken)
        max_joint_force_limit = float(self.terrain_bounds.get("max_joint_force", 1e12))
        max_joint_torque_limit = float(self.terrain_bounds.get("max_joint_torque", 1e12))
        if max_joint_force_limit < 1e11 or max_joint_torque_limit < 1e11:
            force_seen = getattr(self.environment, "_max_reaction_force_seen", 0.0)
            torque_seen = getattr(self.environment, "_max_reaction_torque_seen", 0.0)
            if force_seen > max_joint_force_limit or torque_seen > max_joint_torque_limit:
                failed, failure_reason = True, (
                    f"Joint failure: reaction force {force_seen:.1f}N > {max_joint_force_limit}N or "
                    f"torque {torque_seen:.1f}Nm > {max_joint_torque_limit}Nm"
                )

        if not failed and min_body_y < 0.3: # Shelter collapsed near ground
            failed, failure_reason = True, "Shelter collapsed or fell below ground level"
        elif not failed and core_force > self.max_core_force:
            failed, failure_reason = True, f"Core protection failed: force {core_force:.1f}N > {self.max_core_force}N"
        elif not failed and structure_mass > max_mass:
            failed, failure_reason = True, f"Mass budget exceeded: {structure_mass:.1f}kg > {max_mass}kg"
            
        # Design constraint check (height)
        if not failed:
            for body in self.environment._bodies:
                if body.position.y > self.MAX_STRUCTURE_HEIGHT:
                    failed, failure_reason = True, f"Structure exceeds height limit {self.MAX_STRUCTURE_HEIGHT}m"
                    break

        is_end = (step_count >= max_steps - 1)
        can_eval_success = (step_count >= self.min_steps)
        
        success = can_eval_success and not failed
        done = failed or (is_end and can_eval_success)
        
        score = 100.0 if success else 0.0
        if not done and not failed:
            score = (min(step_count, self.min_steps) / self.min_steps) * 80.0
            
        metrics = {
            'core_force': core_force,
            'max_core_force': self.max_core_force,
            'core_x': self.environment.CORE_X if self.environment else 0,
            'core_y': self.environment.CORE_Y if self.environment else 0,
            'meteor_count': self.environment._meteor_count if self.environment else 0,
            'structure_mass': structure_mass,
            'max_mass': max_mass,
            'max_height_limit': self.MAX_STRUCTURE_HEIGHT,
            'min_body_y': min_body_y,
            'success': success,
            'failed': failed,
            'failure_reason': failure_reason
        }
        if getattr(self.environment, '_max_reaction_force_seen', None) is not None:
            metrics['max_joint_force_seen'] = self.environment._max_reaction_force_seen
        if getattr(self.environment, '_max_reaction_torque_seen', None) is not None:
            metrics['max_joint_torque_seen'] = self.environment._max_reaction_torque_seen
        
        return done, score, metrics

    def get_task_description(self):
        return {
            'task': 'S-05: The Shelter',
            'success_criteria': {
                'protection': f'Core receives <= {self.max_core_force}N force',
                'stability': 'Shelter does not collapse',
                'height_limit': f'No beam above y={self.MAX_STRUCTURE_HEIGHT}m',
                'mass_limit': f'Structure mass <= {self.terrain_bounds.get("max_structure_mass", 300.0)}kg'
            }
        }
