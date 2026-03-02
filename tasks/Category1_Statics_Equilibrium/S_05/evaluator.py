"""
S-05: The Shelter task evaluation module
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """Evaluation system for S-05: The Shelter"""
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        if not environment:
            raise ValueError("Evaluator requires environment instance")
        
        env_class = type(environment)
        try:
            self.KEEP_OUT_RADIUS = env_class.KEEP_OUT_RADIUS
            self.MAX_STRUCTURE_HEIGHT = getattr(env_class, 'MAX_STRUCTURE_HEIGHT', 4.5)
            # Get from instance (may be overridden) or class constant (default)
            self.MAX_MASS = getattr(environment, 'MAX_MASS', env_class.MAX_MASS)
            self.CORE_MAX_FORCE = getattr(environment, 'CORE_MAX_FORCE', env_class.CORE_MAX_FORCE)
        except AttributeError as e:
            raise AttributeError(f"Environment class {env_class.__name__} missing required constant: {e}")
        
        # Use CORE_MAX_FORCE from environment (can be overridden in mutated tasks)
        self.max_core_force = self.CORE_MAX_FORCE
        
        self.design_constraints_checked = False
        
        # Meteor timing: from environment (default 28 meteors, interval 0.85s)
        self.meteor_count = getattr(environment, '_meteor_count', 28)
        self.meteor_spawn_interval = getattr(environment, '_meteor_spawn_interval', 0.85)
        self.total_spawn_time = self.meteor_count * self.meteor_spawn_interval
        self.fall_time = 6.0  # Time for last meteor to fall and impact
        self.min_simulation_time = self.total_spawn_time + self.fall_time
        self.min_steps = int(self.min_simulation_time / TIME_STEP)
        
    def evaluate(self, agent_body, step_count, max_steps):
        """Evaluate shelter performance"""
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        # Get core damage
        core_damage = self.environment.get_core_damage()
        protection_ok = core_damage < self.max_core_force
        
        # Check structure stability (simplified - check if any body fell significantly)
        structure_stable = True
        min_body_y = float('inf')
        max_body_y = float('-inf')
        for body in self.environment._bodies:
            y_pos = body.position.y
            min_body_y = min(min_body_y, y_pos)
            max_body_y = max(max_body_y, y_pos)
            if y_pos < -5.0:  # Fell far below
                structure_stable = False
        
        # Get meteor information
        meteor_count = getattr(self.environment, '_meteors_spawned', 0)
        meteors_impacted = 0
        max_impact_force = 0.0
        
        # Check for meteor impacts (simplified - count meteors that have fallen)
        for meteor in getattr(self.environment, '_meteors', []):
            if meteor.position.y < 5.0:  # Meteor has fallen significantly
                meteors_impacted += 1
        
        # Only check for success after minimum simulation time has passed
        # This ensures all meteors have spawned and had time to fall
        can_evaluate_success = step_count >= self.min_steps
        
        success = protection_ok and structure_stable and can_evaluate_success
        
        # Check failures
        failed = False
        failure_reason = None
        
        if not self.design_constraints_checked and step_count == 0:
            constraint_violations = self._check_design_constraints()
            if constraint_violations:
                failed = True
                failure_reason = "Design constraint violated: " + "; ".join(constraint_violations)
            self.design_constraints_checked = True
        
        if not protection_ok:
            failed = True
            failure_reason = f"Core received {core_damage:.2f}N force (exceeds {self.max_core_force}N limit)"
        elif not structure_stable:
            failed = True
            failure_reason = "Shelter collapsed"
        
        # Calculate score
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            protection_score = (1.0 - min(core_damage / self.max_core_force, 1.0)) * 50.0
            stability_score = 50.0 if structure_stable else 0.0
            score = protection_score + stability_score
        
        # Determine if we should stop (only stop if failed or successfully completed after min time)
        should_stop = failed or (success and can_evaluate_success)
        
        metrics = {
            'core_damage': core_damage,
            'max_core_force': self.max_core_force,
            'structure_stable': structure_stable,
            'structure_mass': self.environment.get_structure_mass(),
            'max_mass': self.MAX_MASS,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'body_count': len(self.environment._bodies),
            'joint_count': len(self.environment._joints),
            'min_body_y': min_body_y if min_body_y != float('inf') else 0.0,
            'max_body_y': max_body_y if max_body_y != float('-inf') else 0.0,
            'meteor_count': meteor_count,
            'meteors_impacted': meteors_impacted,
            'max_impact_force': max(core_damage, max_impact_force),
            'min_steps_required': self.min_steps,
            'can_evaluate_success': can_evaluate_success,
        }
        
        return should_stop, score, metrics
    
    def _check_design_constraints(self):
        """Check design constraints"""
        violations = []
        
        structure_mass = self.environment.get_structure_mass()
        if structure_mass > self.MAX_MASS:
            violations.append(f"Structure mass {structure_mass:.2f}kg exceeds maximum {self.MAX_MASS}kg")
        
        # Check keep-out zone
        for body in self.environment._bodies:
            dist = math.sqrt((body.position.x - 0.0)**2 + (body.position.y - 0.0)**2)
            if dist < self.KEEP_OUT_RADIUS:
                violations.append(f"Beam at ({body.position.x:.2f}, {body.position.y:.2f}) is within {self.KEEP_OUT_RADIUS}m of core")
        
        return violations
    
    def get_task_description(self):
        """Return task description"""
        return {
            'task': 'S-05: The Shelter',
            'description': 'Protect fragile core from falling boulders',
            'success_criteria': {
                'protection': f'Core receives < {self.max_core_force}N force',
                'stability': 'Shelter does not collapse',
                'height_limit': f'No beam above y={self.MAX_STRUCTURE_HEIGHT}m'
            }
        }
