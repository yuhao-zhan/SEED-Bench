"""
K-04: The Pusher task evaluation module
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation system for K-04: The Pusher
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        self.target_distance = float(terrain_bounds.get("target_distance", 10.0))
        self.min_simulation_time = 5.0 # seconds (aligned with description)
        self.min_simulation_steps = int(self.min_simulation_time / TIME_STEP)
        
        self.initial_object_x = 8.0
        self.max_x_reached = 8.0
        self.design_constraints_checked = False

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        # Get object position from environment
        object_pos = self.environment.get_object_position()
        if object_pos is None:
            return False, 0.0, {"error": "Object to push not found"}
            
        current_x, current_y = object_pos
        self.max_x_reached = max(self.max_x_reached, current_x)
        
        failed = False
        failure_reason = None
        
        # Failure: Object fell off the table
        if current_y < -1.0: # Table is at y=0, height 0.5
            failed, failure_reason = True, "Object fell off the platform"
            
        # Success if pushed target distance and survived minimum time
        distance_pushed = current_x - self.initial_object_x
        success = distance_pushed >= self.target_distance and step_count >= self.min_simulation_steps
        
        is_end = (step_count >= max_steps - 1)
        done = failed or is_end
        
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            progress = min(max(0, distance_pushed) / self.target_distance, 1.0)
            score = progress * 70.0
            if step_count > 0:
                score += (min(step_count, self.min_simulation_steps) / self.min_simulation_steps) * 30.0
                
        metrics = {
            'x': current_x,
            'y': current_y,
            'distance': distance_pushed,
            'success': success,
            'failed': failed,
            'failure_reason': failure_reason
        }
        
        return done, score, metrics

    def get_task_description(self):
        return {
            'task': 'K-04: The Pusher',
            'success_criteria': {
                'distance': f'Push object {self.target_distance}m',
                'time': f'Push for {self.min_simulation_time}s'
            }
        }
