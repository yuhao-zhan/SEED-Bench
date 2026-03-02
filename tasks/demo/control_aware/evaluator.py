"""
Control-Aware task evaluation module
Defines task objectives and success criteria with speed limit enforcement
"""
import math


class Evaluator:
    """
    Evaluation system: Defines task objectives and success criteria with speed limit zones
    """
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.start_x = 0.0  # Slider start position
        self.target_x = 30.0  # Target position
        self.max_distance = 0.0  # Maximum distance traveled
        
        # Speed limit tracking
        self.speed_violations = []
        self.speed_violation_count = 0
        
        # Get speed zone limits from environment
        if environment:
            speed_zones = environment.get_speed_zone_limits()
            self.SPEED_ZONE_1_START = speed_zones["zone_1"]["start"]
            self.SPEED_ZONE_1_END = speed_zones["zone_1"]["end"]
            self.SPEED_ZONE_1_LIMIT = speed_zones["zone_1"]["limit"]
            self.SPEED_ZONE_2_START = speed_zones["zone_2"]["start"]
            self.SPEED_ZONE_2_END = speed_zones["zone_2"]["end"]
            self.SPEED_ZONE_2_LIMIT = speed_zones["zone_2"]["limit"]
            self.SPEED_ZONE_3_START = speed_zones["zone_3"]["start"]
            self.SPEED_ZONE_3_END = speed_zones["zone_3"]["end"]
            self.SPEED_ZONE_3_LIMIT = speed_zones["zone_3"]["limit"]
        else:
            raise ValueError("Evaluator requires environment instance")
        
        self.max_x_reached = 0.0  # Track maximum x reached
        
    def _get_speed_limit(self, x_position):
        """Get speed limit for current position"""
        if self.SPEED_ZONE_1_START <= x_position < self.SPEED_ZONE_1_END:
            return self.SPEED_ZONE_1_LIMIT
        elif self.SPEED_ZONE_2_START <= x_position < self.SPEED_ZONE_2_END:
            return self.SPEED_ZONE_2_LIMIT
        elif self.SPEED_ZONE_3_START <= x_position < self.SPEED_ZONE_3_END:
            return self.SPEED_ZONE_3_LIMIT
        else:
            # Before start or after target - use Zone 1 limit as default
            return self.SPEED_ZONE_1_LIMIT
    
    def _get_current_zone(self, x_position):
        """Get current speed zone name"""
        if self.SPEED_ZONE_1_START <= x_position < self.SPEED_ZONE_1_END:
            return "Zone 1"
        elif self.SPEED_ZONE_2_START <= x_position < self.SPEED_ZONE_2_END:
            return "Zone 2"
        elif self.SPEED_ZONE_3_START <= x_position < self.SPEED_ZONE_3_END:
            return "Zone 3"
        else:
            return "Outside zones"
        
    def evaluate(self, agent_components, step_count, max_steps):
        """
        Evaluate Agent performance
        Args:
            agent_components: Dictionary with 'slider' key
            step_count: Current step count
            max_steps: Maximum steps
        Returns: (success, score, metrics)
        """
        if not agent_components or 'slider' not in agent_components:
            return False, 0.0, {'error': 'Missing slider in agent_components'}
        
        slider = agent_components['slider']
        
        # Get slider state
        if not self.environment:
            return False, 0.0, {'error': 'Environment not provided'}
        
        position_x, velocity_x = self.environment.get_slider_state(slider)
        position_y = slider.position.y
        
        # Track maximum x reached
        if position_x > self.max_x_reached:
            self.max_x_reached = position_x
        
        # Calculate travel distance
        distance_traveled = position_x - self.start_x
        
        # Update maximum distance
        if distance_traveled > self.max_distance:
            self.max_distance = distance_traveled
        
        # Check speed limit violation (CRITICAL - immediate failure)
        speed_limit = self._get_speed_limit(position_x)
        speed_violated = False
        if position_x >= self.SPEED_ZONE_1_START and position_x < self.SPEED_ZONE_3_END:
            # Only check speed limits within the speed zones
            if velocity_x > speed_limit:  # Speed must not exceed limit
                speed_violated = True
                self.speed_violation_count += 1
                self.speed_violations.append({
                    'step': step_count,
                    'x_position': position_x,
                    'speed': velocity_x,
                    'limit': speed_limit,
                    'zone': self._get_current_zone(position_x)
                })
        
        # Check if successful (reached target position)
        success = position_x >= self.target_x
        
        # Check if failed
        failed = False
        failure_reason = None
        
        # Failure condition 1: Speed limit violation (CRITICAL)
        if speed_violated:
            failed = True
            current_zone = self._get_current_zone(position_x)
            failure_reason = f"Speed limit violated in {current_zone}: speed {velocity_x:.2f} m/s exceeds limit {speed_limit:.2f} m/s"
        
        # Failure condition 2: Fell off track
        if position_y < self.environment.SLIDER_MIN_Y or position_y > self.environment.SLIDER_MAX_Y:
            failed = True
            failure_reason = f"Slider fell off track (y={position_y:.2f}m, track y={self.environment.TRACK_Y}m)"
        
        # Failure condition 3: Moved backward (slider cannot go backward)
        if position_x < self.max_x_reached - 0.5:
            failed = True
            failure_reason = f"Slider moved backward (current x={position_x:.2f}m, max x={self.max_x_reached:.2f}m)"
        
        # Failure condition 4: Timeout
        if step_count >= max_steps and not success:
            failed = True
            failure_reason = f"Timeout: did not reach target position within {max_steps} steps"
        
        # Calculate score (0-100)
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            # Calculate score based on travel distance
            progress = min(distance_traveled / (self.target_x - self.start_x), 1.0)
            score = progress * 80.0  # Max 80 points, success gets additional 20 points
        
        # Collect metrics
        current_zone = self._get_current_zone(position_x)
        speed_limit = self._get_speed_limit(position_x)
        
        metrics = {
            'distance_traveled': distance_traveled,
            'current_x': position_x,
            'current_y': position_y,
            'target_x': self.target_x,
            'progress': min(distance_traveled / (self.target_x - self.start_x), 1.0) * 100,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            'max_distance': self.max_distance,
            'velocity_x': velocity_x,
            'current_zone': current_zone,
            'speed_limit': speed_limit,
            'speed_violated': speed_violated,
            'speed_violation_count': self.speed_violation_count,
            'max_x_reached': self.max_x_reached
        }
        
        return success or failed, score, metrics
    
    def get_task_description(self):
        """Return task description"""
        return {
            'task': 'Control slider speed based on position to comply with speed limits',
            'description': 'Agent needs to control a slider that dynamically adjusts speed based on position',
            'start_position': self.start_x,
            'target_position': self.target_x,
            'speed_zones': {
                'zone_1': {'start': self.SPEED_ZONE_1_START, 'end': self.SPEED_ZONE_1_END, 'limit': self.SPEED_ZONE_1_LIMIT},
                'zone_2': {'start': self.SPEED_ZONE_2_START, 'end': self.SPEED_ZONE_2_END, 'limit': self.SPEED_ZONE_2_LIMIT},
                'zone_3': {'start': self.SPEED_ZONE_3_START, 'end': self.SPEED_ZONE_3_END, 'limit': self.SPEED_ZONE_3_LIMIT},
            },
            'success_criteria': {
                'primary': f'Slider must reach position x={self.target_x}m',
                'speed_compliance': 'Slider must never exceed speed limits in any zone',
                'constraint_track': 'Slider cannot fall off track',
                'constraint_backward': 'Slider cannot move backward'
            },
            'evaluation': {
                'score_range': '0-100',
                'success_score': 100,
                'partial_score': 'Based on travel distance, max 80 points',
                'failure_score': 0
            }
        }
