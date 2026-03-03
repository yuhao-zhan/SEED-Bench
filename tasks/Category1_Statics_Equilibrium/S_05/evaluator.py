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
        
        self.max_core_force = float(terrain_bounds.get("core_max_force", 150.0))
        self.MAX_STRUCTURE_HEIGHT = float(terrain_bounds.get("max_structure_height", 7.5))
        self.CORE_Y = 1.0 # From environment
        
        # Simulation phase tracking
        meteor_count = terrain_bounds.get("meteor_count", 12)
        interval = terrain_bounds.get("meteor_spawn_interval", 30)
        fall_time = 6.0 # seconds for last meteor
        self.min_steps = (meteor_count * interval) + int(fall_time / TIME_STEP)
        
        self.design_constraints_checked = False

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        core_force = self.environment.get_core_max_force()
        
        failed = False
        failure_reason = None
        
        # Check stability: any part of the shelter fell too low
        min_body_y = 100.0
        for body in self.environment._bodies:
            min_body_y = min(min_body_y, body.position.y)
        
        if min_body_y < 0.5: # Shelter collapsed near ground/core
            failed, failure_reason = True, "Shelter collapsed"
        elif core_force > self.max_core_force:
            failed, failure_reason = True, f"Core protection failed: force {core_force:.1f}N > {self.max_core_force}N"
            
        # Design constraint check (height)
        if not failed:
            for body in self.environment._bodies:
                if body.position.y > self.MAX_STRUCTURE_HEIGHT + 0.5: # Margin for beam half-height
                    failed, failure_reason = True, f"Structure exceeds height limit {self.MAX_STRUCTURE_HEIGHT}m"
                    break

        is_end = (step_count >= max_steps - 1)
        # can_evaluate_success after all meteors should have landed
        can_eval_success = (step_count >= self.min_steps)
        
        success = can_eval_success and not failed
        done = failed or (is_end and can_eval_success)
        
        score = 100.0 if success else 0.0
        if not done:
            # Partial score based on meteor phase completion
            score = (min(step_count, self.min_steps) / self.min_steps) * 80.0
            
        metrics = {
            'core_force': core_force,
            'max_core_force': self.max_core_force,
            'min_body_y': min_body_y,
            'success': success,
            'failed': failed,
            'failure_reason': failure_reason
        }
        
        return done, score, metrics

    def get_task_description(self):
        return {
            'task': 'S-05: The Shelter',
            'success_criteria': {
                'protection': f'Core receives < {self.max_core_force}N force',
                'stability': 'Shelter does not collapse',
                'height_limit': f'No beam above y={self.MAX_STRUCTURE_HEIGHT}m'
            }
        }
