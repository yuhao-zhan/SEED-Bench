"""
K-06: The Wiper task evaluation module
"""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation system for K-06: The Wiper
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        self.min_removal_ratio = 0.8 # 80% removal (aligned with env 20% residual fail)
        self.min_simulation_time = 8.0 # seconds (aligned with description)
        self.min_simulation_steps = int(self.min_simulation_time / TIME_STEP)
        
        self.design_constraints_checked = False

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        initial_count = self.environment.get_initial_particle_count()
        remaining_count = self.environment.get_remaining_particle_count()
        
        if initial_count == 0:
            return False, 0.0, {"error": "No particles found"}
            
        removal_ratio = (initial_count - remaining_count) / initial_count
        
        failed = False
        failure_reason = None
        
        # Failure: Not enough particles removed by the end
        is_end = (step_count >= max_steps - 1)
        if is_end and removal_ratio < self.min_removal_ratio:
            failed, failure_reason = True, f"Wiper failed: only {removal_ratio*100:.1f}% removed (need {self.min_removal_ratio*100:.0f}%)"
            
        # Success if reached target removal and survived minimum time
        success = removal_ratio >= self.min_removal_ratio and step_count >= self.min_simulation_steps
        
        done = failed or is_end
        
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            progress = min(removal_ratio / self.min_removal_ratio, 1.0)
            score = progress * 70.0
            if step_count > 0:
                score += (min(step_count, self.min_simulation_steps) / self.min_simulation_steps) * 30.0
                
        metrics = {
            'initial_count': initial_count,
            'remaining_count': remaining_count,
            'removal_ratio': removal_ratio,
            'success': success,
            'failed': failed,
            'failure_reason': failure_reason
        }
        
        return done, score, metrics

    def get_task_description(self):
        return {
            'task': 'K-06: The Wiper',
            'success_criteria': {
                'removal': f'Remove {self.min_removal_ratio*100:.0f}% of particles',
                'time': f'Wipe for {self.min_simulation_time}s'
            }
        }
