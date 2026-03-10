"""
S-06: The Overhang task evaluation module
Enhanced for structural complexity and mass constraints.
"""
import math
from Box2D.b2 import polygonShape


class Evaluator:
    """Evaluation system for S-06: The Overhang"""
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.stability_time = 10.0
        self.target_overhang = 0.1
        
        # Override target parameters
        if environment and hasattr(environment, '_terrain_config'):
            self.target_overhang = environment._terrain_config.get("target_overhang", 0.1)
            self.stability_time = environment._terrain_config.get("stability_time", 10.0)
        
        self.max_x_position = 0.0
        self.stability_start_time = None
        self.stable_duration = 0.0
        self.last_max_x = 0.0
        
        # Track structure state
        self.min_y_position = float('inf')
        self.max_y_position = float('-inf')
        self.structure_mass = 0.0
        self.total_kinetic_energy = 0.0
        self.max_velocity = 0.0
        
        if not environment:
            raise ValueError("Evaluator requires environment instance")
        
        env_class = type(environment)
        self.MAX_BLOCK_LENGTH = env_class.MAX_BLOCK_LENGTH
        self.MAX_BLOCK_HEIGHT = env_class.MAX_BLOCK_HEIGHT
        self.MAX_BLOCK_COUNT = env_class.MAX_BLOCK_COUNT
        self.START_ZONE_X_MAX = env_class.START_ZONE_X_MAX
        self.SPAWN_ZONE = terrain_bounds.get("spawn_zone", [-10.0, 0.0])
        self.MAX_TOTAL_MASS = 20000.0  # INCREASED for extreme difficulty support
        
        self.design_constraints_checked = False
        self.persistently_failed = False
        self.persistent_failure_reason = None
        
    def evaluate(self, agent_body, step_count, max_steps):
        """Evaluate overhang performance"""
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        # Table velocity for relative stability
        table_vel = (0, 0)
        if hasattr(self.environment, '_terrain_bodies') and 'table' in self.environment._terrain_bodies:
            table_vel = self.environment._terrain_bodies['table'].linearVelocity

        current_max_x = self.environment.get_max_x_position()
        self.max_x_position = max(self.max_x_position, current_max_x)
        
        if self.environment._bodies:
            y_positions = [b.position.y for b in self.environment._bodies]
            self.min_y_position = min(y_positions)
            self.max_y_position = max(y_positions)
            self.structure_mass = self.environment.get_structure_mass()
            
            self.total_kinetic_energy = 0.0
            self.max_velocity = 0.0
            for body in self.environment._bodies:
                vx, vy = body.linearVelocity
                rel_vx = vx - table_vel[0]
                rel_vy = vy - table_vel[1]
                
                velocity = math.sqrt(rel_vx*rel_vx + rel_vy*rel_vy)
                self.max_velocity = max(self.max_velocity, velocity)
                kinetic_energy = 0.5 * body.mass * velocity * velocity
                self.total_kinetic_energy += kinetic_energy
        
        time_step = 1.0 / 60.0
        current_time = step_count * time_step
        
        # Relative stability
        is_moving = self.max_velocity > 0.01 or self.total_kinetic_energy > 0.01
        if not is_moving:
            if self.stability_start_time is None:
                self.stability_start_time = current_time
            self.stable_duration = current_time - self.stability_start_time
        else:
            self.stability_start_time = None
            self.stable_duration = 0.0
        
        self.last_max_x = current_max_x
        
        stability_ok = self.stable_duration >= self.stability_time - 0.01
        overhang_ok = self.max_x_position >= self.target_overhang - 0.01
        success = stability_ok and overhang_ok
        
        # Persistent Failure Checks
        if not self.design_constraints_checked and step_count == 0:
            constraint_violations = self._check_design_constraints()
            if constraint_violations:
                self.persistently_failed = True
                self.persistent_failure_reason = "Design constraint violated: " + "; ".join(constraint_violations)
            self.design_constraints_checked = True
        
        if self.environment._bodies:
            if self.min_y_position < -5.0:
                self.persistently_failed = True
                self.persistent_failure_reason = "Structure fell off table"
            
            if self.structure_mass > self.MAX_TOTAL_MASS + 0.01:
                self.persistently_failed = True
                self.persistent_failure_reason = f"Structure exceeds maximum mass: {self.structure_mass:.2f} > {self.MAX_TOTAL_MASS}"
        
        if "ceiling_y" in self.terrain_bounds:
            cy = self.terrain_bounds["ceiling_y"]
            if self.max_y_position > cy + 0.01:
                self.persistently_failed = True
                self.persistent_failure_reason = f"Structure hit the ceiling at y={cy}m"

        failed = self.persistently_failed
        failure_reason = self.persistent_failure_reason

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
            'min_y_position': self.min_y_position,
            'max_y_position': self.max_y_position,
            'structure_mass': self.structure_mass,
            'total_kinetic_energy': self.total_kinetic_energy,
            'max_velocity': self.max_velocity,
            'block_count': len(self.environment._bodies),
            'max_block_count_limit': self.MAX_BLOCK_COUNT,
            'max_total_mass_limit': self.MAX_TOTAL_MASS,
            'ceiling_y_limit': self.terrain_bounds.get("ceiling_y", None)
        }
        
        # Calculate Center of Mass
        if self.environment._bodies:
            total_mass = sum(b.mass for b in self.environment._bodies)
            if total_mass > 0:
                com_x = sum(b.position.x * b.mass for b in self.environment._bodies) / total_mass
                com_y = sum(b.position.y * b.mass for b in self.environment._bodies) / total_mass
                metrics['center_of_mass_x'] = com_x
                metrics['center_of_mass_y'] = com_y
        
        return success or failed, score, metrics
    
    def _check_design_constraints(self):
        violations = []
        if len(self.environment._bodies) > self.MAX_BLOCK_COUNT:
            violations.append(f"Too many blocks: {len(self.environment._bodies)} > {self.MAX_BLOCK_COUNT}")
        
        for body in self.environment._bodies:
            # Check restricted spawn zone (ONLY for center position)
            if not (self.SPAWN_ZONE[0] - 0.01 <= body.position.x <= self.SPAWN_ZONE[1] + 0.01):
                violations.append(f"Block center at x={body.position.x:.2f} is outside spawn zone [{self.SPAWN_ZONE[0]}, {self.SPAWN_ZONE[1]}]")
            
            for fixture in body.fixtures:
                shape = fixture.shape
                if isinstance(shape, polygonShape):
                    width = (shape.vertices[1][0] - shape.vertices[0][0])
                    height = (shape.vertices[2][1] - shape.vertices[1][1])
                    if width > self.MAX_BLOCK_LENGTH + 0.01:
                        violations.append(f"Block width {width:.2f}m exceeds maximum {self.MAX_BLOCK_LENGTH}m")
                    if height > self.MAX_BLOCK_HEIGHT + 0.01:
                        violations.append(f"Block height {height:.2f}m exceeds maximum {self.MAX_BLOCK_HEIGHT}m")
        return violations
    
    def get_task_description(self):
        return {
            'task': 'S-06: The Overhang',
            'description': 'Stack blocks to create maximum overhang under severe physical constraints',
            'target_overhang': self.target_overhang,
            'success_criteria': {
                'stability': f'Structure stays still for {self.stability_time}s',
                'overhang': f'Max x position > {self.target_overhang}m',
                'mass': f'Total mass must be <= {self.MAX_TOTAL_MASS} units'
            }
        }
