"""
S-06: The Overhang task evaluation module
"""
import math
from Box2D.b2 import polygonShape


class Evaluator:
    """Evaluation system for S-06: The Overhang"""
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.stability_time = 10.0
        self.target_overhang = 0.1  # Reduced from 2.0m to 0.1m to make task easier
        
        self.max_x_position = 0.0
        self.stability_start_time = None
        self.stable_duration = 0.0
        self.last_max_x = 0.0
        self.stability_check_interval = 1.0  # Check every second
        
        # Track structure state for detailed metrics
        self.min_y_position = float('inf')
        self.max_y_position = float('-inf')
        self.structure_mass = 0.0
        self.center_of_mass_x = 0.0
        self.center_of_mass_y = 0.0
        self.total_kinetic_energy = 0.0
        self.max_velocity = 0.0
        
        if not environment:
            raise ValueError("Evaluator requires environment instance")
        
        env_class = type(environment)
        try:
            self.MAX_BLOCK_LENGTH = env_class.MAX_BLOCK_LENGTH
            self.MAX_BLOCK_HEIGHT = env_class.MAX_BLOCK_HEIGHT
            self.MAX_BLOCK_COUNT = env_class.MAX_BLOCK_COUNT
            self.START_ZONE_X_MAX = env_class.START_ZONE_X_MAX
        except AttributeError as e:
            raise AttributeError(f"Environment class {env_class.__name__} missing required constant: {e}")
        
        self.design_constraints_checked = False
        
    def evaluate(self, agent_body, step_count, max_steps):
        """Evaluate overhang performance"""
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        # Get max x position (considering block width - right edge position)
        # Calculate the right edge of each block (center_x + width/2)
        if self.environment._bodies:
            max_right_edge = float('-inf')
            max_center_x = float('-inf')
            for body in self.environment._bodies:
                center_x = body.position.x
                max_center_x = max(max_center_x, center_x)
                # Get block width from fixtures
                for fixture in body.fixtures:
                    shape = fixture.shape
                    if isinstance(shape, polygonShape):
                        if hasattr(shape, 'box'):
                            box = shape.box
                            if isinstance(box, tuple) and len(box) >= 2:
                                width = box[0] * 2  # box is half-width
                                right_edge = center_x + width / 2
                                max_right_edge = max(max_right_edge, right_edge)
            # Use right edge if calculated, otherwise use center position
            if max_right_edge != float('-inf'):
                current_max_x = max_right_edge
            else:
                current_max_x = max_center_x
        else:
            current_max_x = self.environment.get_max_x_position()
        self.max_x_position = max(self.max_x_position, current_max_x)
        
        # Calculate detailed structure metrics
        if self.environment._bodies:
            # Structure bounds
            y_positions = [b.position.y for b in self.environment._bodies]
            self.min_y_position = min(y_positions)
            self.max_y_position = max(y_positions)
            
            # Structure mass
            self.structure_mass = self.environment.get_structure_mass()
            
            # Center of mass
            total_mass = 0.0
            com_x = 0.0
            com_y = 0.0
            for body in self.environment._bodies:
                mass = body.mass
                total_mass += mass
                com_x += body.position.x * mass
                com_y += body.position.y * mass
            
            if total_mass > 0:
                self.center_of_mass_x = com_x / total_mass
                self.center_of_mass_y = com_y / total_mass
            
            # Kinetic energy and velocity
            self.total_kinetic_energy = 0.0
            self.max_velocity = 0.0
            for body in self.environment._bodies:
                vx, vy = body.linearVelocity
                velocity = math.sqrt(vx*vx + vy*vy)
                self.max_velocity = max(self.max_velocity, velocity)
                kinetic_energy = 0.5 * body.mass * velocity * velocity
                self.total_kinetic_energy += kinetic_energy
        
        # Check stability (structure doesn't move)
        time_step = 1.0 / 60.0
        current_time = step_count * time_step
        
        # Check if max_x changed significantly (structure moved)
        x_changed = abs(current_max_x - self.last_max_x) > 0.01  # 1cm threshold
        
        if not x_changed:
            if self.stability_start_time is None:
                self.stability_start_time = current_time
            self.stable_duration = current_time - self.stability_start_time
        else:
            self.stability_start_time = None
            self.stable_duration = 0.0
        
        self.last_max_x = current_max_x
        
        # Check success
        stability_ok = self.stable_duration >= self.stability_time
        overhang_ok = self.max_x_position >= self.target_overhang
        
        success = stability_ok and overhang_ok
        
        # Check failures
        failed = False
        failure_reason = None
        
        if not self.design_constraints_checked and step_count == 0:
            constraint_violations = self._check_design_constraints()
            if constraint_violations:
                failed = True
                failure_reason = "Design constraint violated: " + "; ".join(constraint_violations)
            self.design_constraints_checked = True
        
        # Check if structure fell
        if self.environment._bodies:
            min_y = min(b.position.y for b in self.environment._bodies)
            if min_y < -5.0:  # Fell far below table
                failed = True
                failure_reason = "Structure fell off table"
        
        # Calculate score
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            stability_score = min(self.stable_duration / self.stability_time, 1.0) * 50.0
            overhang_score = min(self.max_x_position / self.target_overhang, 1.0) * 50.0
            score = stability_score + overhang_score
        
        metrics = {
            'max_x_position': self.max_x_position,
            'target_overhang': self.target_overhang,
            'stable_duration': self.stable_duration,
            'target_stability_time': self.stability_time,
            'stability_ok': stability_ok,
            'overhang_ok': overhang_ok,
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
            'step_count': step_count,
            # Additional physical metrics
            'structure_mass': self.structure_mass,
            'block_count': len(self.environment._bodies) if self.environment._bodies else 0,
            'min_y_position': self.min_y_position if self.min_y_position != float('inf') else 0.0,
            'max_y_position': self.max_y_position if self.max_y_position != float('-inf') else 0.0,
            'center_of_mass_x': self.center_of_mass_x,
            'center_of_mass_y': self.center_of_mass_y,
            'total_kinetic_energy': self.total_kinetic_energy,
            'max_velocity': self.max_velocity,
            'current_max_x': current_max_x,
        }
        
        return success or failed, score, metrics
    
    def _check_design_constraints(self):
        """Check design constraints"""
        violations = []
        
        # Check block count
        if len(self.environment._bodies) > self.MAX_BLOCK_COUNT:
            violations.append(f"Too many blocks: {len(self.environment._bodies)} > {self.MAX_BLOCK_COUNT}")
        
        # Check block sizes and positions
        for body in self.environment._bodies:
            # Check position
            if body.position.x >= self.START_ZONE_X_MAX:
                violations.append(f"Block at x={body.position.x:.2f} is not in start zone (x < {self.START_ZONE_X_MAX})")
            
            # Check size
            for fixture in body.fixtures:
                shape = fixture.shape
                if isinstance(shape, polygonShape):
                    if hasattr(shape, 'box'):
                        box = shape.box
                        if isinstance(box, tuple) and len(box) >= 2:
                            width = box[0] * 2
                            height = box[1] * 2
                            if width > self.MAX_BLOCK_LENGTH:
                                violations.append(f"Block width {width:.2f}m exceeds maximum {self.MAX_BLOCK_LENGTH}m")
                            if height > self.MAX_BLOCK_HEIGHT:
                                violations.append(f"Block height {height:.2f}m exceeds maximum {self.MAX_BLOCK_HEIGHT}m")
        
        return violations
    
    def get_task_description(self):
        """Return task description"""
        return {
            'task': 'S-06: The Overhang',
            'description': 'Stack blocks to create maximum overhang',
            'target_overhang': self.target_overhang,
            'success_criteria': {
                'stability': f'Structure stays still for {self.stability_time}s',
                'overhang': f'Max x position > {self.target_overhang}m'
            }
        }
