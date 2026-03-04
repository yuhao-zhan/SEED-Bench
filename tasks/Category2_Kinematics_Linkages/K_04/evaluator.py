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
        self.min_simulation_time = 10.0 # seconds (aligned with prompt description)
        self.min_simulation_steps = int(self.min_simulation_time / TIME_STEP)
        
        self.initial_object_x = 8.0
        self.max_x_reached = 8.0
        self.max_pusher_tilt = 0.0
        self.design_constraints_checked = False

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return (False, 0.0, {"error": "Environment not available"})
        
        # Get object position from environment
        object_pos = self.environment.get_object_position()
        if object_pos is None:
            return (False, 0.0, {"error": "Object to push not found"})
            
        current_object_x, current_object_y = object_pos
        self.max_x_reached = max(self.max_x_reached, current_object_x)
        
        # Robust pusher tracking
        pusher = agent_body
        if pusher is None and self.environment._bodies:
            pusher = self.environment._bodies[0]
            
        pusher_x, pusher_y, pusher_angle = 0.0, 0.0, 0.0
        if pusher:
            pusher_x = pusher.position.x
            pusher_y = pusher.position.y
            pusher_angle = pusher.angle
            # Normalize angle to [-pi, pi]
            while pusher_angle > math.pi: pusher_angle -= 2 * math.pi
            while pusher_angle < -math.pi: pusher_angle += 2 * math.pi
            self.max_pusher_tilt = max(self.max_pusher_tilt, abs(pusher_angle))

        failed = False
        failure_reason = None
        
        # Failure: Object fell off the platform (ground level is y=1.0)
        if current_object_y < 0.5:
            failed = True
            failure_reason = "Object fell off the platform"
            
        # Failure: Pusher tipped over (tilt > 30 degrees = pi/6 radians)
        if abs(pusher_angle) > math.pi / 6:
            failed = True
            failure_reason = f"Pusher tipped over: tilt angle {abs(pusher_angle):.3f} rad exceeds limit \u00b1\u03c0/6 (\u00b130\u00b0)"

        # Success if pushed target distance and survived minimum time
        distance_pushed = current_object_x - self.initial_object_x
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
            'object_x': current_object_x,
            'object_y': current_object_y,
            'pusher_x': pusher_x,
            'pusher_y': pusher_y,
            'pusher_angle': pusher_angle,
            'distance_pushed': distance_pushed,
            'max_distance_pushed': self.max_x_reached - self.initial_object_x,
            'max_pusher_tilt': self.max_pusher_tilt,
            'pusher_tipped': abs(pusher_angle) > math.pi / 6,
            'target_object_x': self.initial_object_x + self.target_distance,
            'progress': progress * 100.0 if 'progress' in locals() else 0.0,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'min_simulation_steps_required': self.min_simulation_steps,
            'structure_mass': self.environment.get_structure_mass(),
            'max_structure_mass': getattr(self.environment, 'MAX_STRUCTURE_MASS', 40.0),
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
