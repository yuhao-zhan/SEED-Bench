"""
K-01: The Walker task evaluation module
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation system for K-01: The Walker
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        self.target_distance = float(terrain_bounds.get("target_distance", 15.0))
        self.initial_x = float(terrain_bounds.get("initial_x", 10.0))
        self.min_torso_height = 1.2 # Lowered from 1.5 to provide better margin from 2.0 start
        self.min_simulation_time = 15.0 # seconds
        self.min_simulation_steps = int(self.min_simulation_time / TIME_STEP)
        self.max_x_reached = self.initial_x
        self.min_torso_y = 2.0  # Starting torso height approx 2.0m

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return (False, 0.0, {"error": "Environment not available"})
        
        # Robust torso tracking
        torso = agent_body
        if torso is None and self.environment._bodies:
            torso = self.environment._bodies[0]
            
        if torso is None:
            return (False, 0.0, {"error": "Walker torso not found"})
            
        current_x = torso.position.x
        current_y = torso.position.y
        self.max_x_reached = max(self.max_x_reached, current_x)
        self.min_torso_y = min(self.min_torso_y, current_y)
        
        failed = False
        failure_reason = None
        
        # Failure: Torso fell too low
        if current_y < self.min_torso_height:
            failed = True
            failure_reason = f"Walker collapsed: torso touched ground (height {current_y:.2f}m < {self.min_torso_height}m)"
        
        # Failure: Mass budget exceeded (design constraint)
        max_structure_mass = getattr(self.environment, 'MAX_STRUCTURE_MASS', 100.0)
        structure_mass = self.environment.get_structure_mass()
        if structure_mass > max_structure_mass:
            failed = True
            failure_reason = (
                failure_reason + "; " if failure_reason else ""
            ) + f"Design constraint violated: structure mass {structure_mass:.2f}kg exceeds budget {max_structure_mass:.1f}kg"

        # Failure: Torso (main body) left the build zone. Use y_min = min_torso_height (1.2) so that
        # "build zone" for torso aligns with stability (torso > 1.2); legs can extend to ground for traction.
        build_zone = self.terrain_bounds.get("build_zone", {})
        x_range = build_zone.get("x", [0.0, 50.0])
        y_range = build_zone.get("y", [2.0, 10.0])
        x_min, x_max = float(x_range[0]), float(x_range[1])
        y_max = float(y_range[1])
        y_min = self.min_torso_height  # Torso build zone: allow down to 1.2m (stability limit), not 2.0
        if current_x < x_min or current_x > x_max or current_y < y_min or current_y > y_max:
            failed = True
            failure_reason = (
                failure_reason + "; " if failure_reason else ""
            ) + f"Build zone violated: torso at ({current_x:.2f}, {current_y:.2f}) is outside allowed region x=[{x_min}, {x_max}], y=[{y_min:.1f}, {y_max}]."
            
        # Success if reached target distance and survived minimum time
        distance_traveled = current_x - self.initial_x
        progress = min(max(0, distance_traveled) / self.target_distance, 1.0)
        success = distance_traveled >= self.target_distance and step_count >= self.min_simulation_steps
        
        is_end = (step_count >= max_steps - 1)
        done = failed or success or is_end
        
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            score = progress * 70.0
            if step_count > 0:
                score += (min(step_count, self.min_simulation_steps) / self.min_simulation_steps) * 30.0
                
        target_x = self.initial_x + self.target_distance
        metrics = {
            'walker_x': current_x,
            'walker_y': current_y,
            'distance_traveled': distance_traveled,
            'max_x_reached': self.max_x_reached,
            'min_torso_y': self.min_torso_y,
            'progress': progress * 100.0,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'min_simulation_steps_required': self.min_simulation_steps,
            'structure_mass': structure_mass,
            'max_structure_mass': max_structure_mass,
            'target_x': target_x,
        }
        
        return done, score, metrics

    def get_task_description(self):
        return {
            'task': 'K-01: The Walker',
            'success_criteria': {
                'distance': f'Travel {self.target_distance}m',
                'height': f'Keep torso y > {self.min_torso_height}m',
                'time': f'Survive for {self.min_simulation_time}s'
            }
        }
