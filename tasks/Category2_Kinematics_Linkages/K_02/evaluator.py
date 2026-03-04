"""
K-02: The Climber task evaluation module
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation system for K-02: The Climber
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        self.target_height = float(terrain_bounds.get("target_height", 15.0))
        self.min_simulation_time = 10.0 # seconds (aligned with description)
        self.min_simulation_steps = int(self.min_simulation_time / TIME_STEP)
        
        self.initial_y = 5.0
        self.max_y_reached = 5.0
        self.min_height_seen = 5.0
        self.design_constraints_checked = False

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return (False, 0.0, {"error": "Environment not available"})
        
        # Robust body tracking
        body = agent_body
        if body is None and self.environment._bodies:
            body = self.environment._bodies[0]
            
        if body is None:
            return (False, 0.0, {"error": "Climber body not found"})
            
        current_x = body.position.x
        current_y = body.position.y
        self.max_y_reached = max(self.max_y_reached, current_y)
        self.min_height_seen = min(self.min_height_seen, current_y)
        
        failed = False
        failure_reason = None
        
        # Failure: Fell below ground level (safety margin)
        if current_y < 1.0:
            failed = True
            failure_reason = "Climber fell: touched the ground (height < 1.0m)"
        
        # Failure: Left the wall vicinity (x in [3.0, 5.5])
        if not (3.0 <= current_x <= 5.5):
            failed = True
            failure_reason = f"Climber lost wall contact: x={current_x:.2f}m (required x in [3.0, 5.5]m)"
            
        # Success if reached target height and survived minimum time
        height_gained = current_y - self.initial_y
        success = height_gained >= self.target_height and step_count >= self.min_simulation_steps
        
        is_end = (step_count >= max_steps - 1)
        done = failed or is_end
        
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            progress = min(max(0, height_gained) / self.target_height, 1.0)
            score = progress * 70.0
            if step_count > 0:
                score += (min(step_count, self.min_simulation_steps) / self.min_simulation_steps) * 30.0
                
        metrics = {
            'climber_x': current_x,
            'climber_y': current_y,
            'height_gained': height_gained,
            'max_height_reached': self.max_y_reached,
            'min_height_seen': self.min_height_seen,
            'climber_fell': current_y < 2.0, # Visual fall indication
            'target_y': self.initial_y + self.target_height,
            'progress': progress * 100.0 if 'progress' in locals() else 0.0,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'min_simulation_steps_required': self.min_simulation_steps,
            'structure_mass': self.environment.get_structure_mass(),
            'max_structure_mass': getattr(self.environment, 'MAX_STRUCTURE_MASS', 50.0),
        }
        
        return done, score, metrics

    def get_task_description(self):
        return {
            'task': 'K-02: The Climber',
            'success_criteria': {
                'height': f'Reach height {self.target_height}m',
                'time': f'Climb for {self.min_simulation_time}s'
            }
        }
