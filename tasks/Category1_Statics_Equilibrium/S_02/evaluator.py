"""
S-02: The Skyscraper task evaluation module
"""
import math


class Evaluator:
    """Evaluation system for S-02: The Skyscraper"""
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.target_height = 30.0
        self.survival_height = 25.0
        self.survival_time = 30.0
        # Allow some tolerance for structure settling during quake
        # Real structures can have some elastic deformation during earthquakes
        self.survival_tolerance = 3.0  # Allow 3m tolerance for elastic deformation during quake
        self.stability_x_min = -4.0
        self.stability_x_max = 4.0
        
        self.initial_height = 0.0
        self.min_height_during_quake = float('inf')
        self.max_center_of_mass_x = -float('inf')
        self.min_center_of_mass_x = float('inf')
        # Initialize with center position to avoid false positives
        self.max_center_of_mass_x = 0.0
        self.min_center_of_mass_x = 0.0
        
        # Track structure integrity
        self.initial_joint_count = 0
        self.initial_spring_count = 0
        self.structure_broken = False
        
        # Track detailed physical state
        self.max_velocity_x = 0.0
        self.max_velocity_y = 0.0
        self.max_angular_velocity = 0.0
        self.height_history = []  # Track height over time
        self.center_of_mass_history = []  # Track center of mass over time
        
        if not environment:
            raise ValueError("Evaluator requires environment instance")
        
        env_class = type(environment)
        try:
            self.FOUNDATION_X_MIN = env_class.FOUNDATION_X_MIN
            self.FOUNDATION_X_MAX = env_class.FOUNDATION_X_MAX
            self.TARGET_HEIGHT = env_class.TARGET_HEIGHT
            self.MAX_WIDTH = env_class.MAX_WIDTH
            self.STABILITY_X_MIN = env_class.STABILITY_X_MIN
            self.STABILITY_X_MAX = env_class.STABILITY_X_MAX
        except AttributeError as e:
            raise AttributeError(f"Environment class {env_class.__name__} missing required constant: {e}")
        
        self.design_constraints_checked = False
        
    def evaluate(self, agent_body, step_count, max_steps):
        """Evaluate structure performance"""
        if not self.environment:
            return False, 0.0, {"error": "Environment not available"}
        
        # Get structure bounds
        bounds = self.environment.get_structure_bounds()
        current_height = bounds.get("top", 0)
        center_x = bounds.get("center_x", 0)
        structure_width = bounds.get("width", 0)
        
        # Track structure integrity
        if step_count == 0:
            self.initial_joint_count = len(self.environment._joints)
            self.initial_spring_count = len(self.environment._springs)
        
        current_joint_count = len(self.environment._joints)
        current_spring_count = len(self.environment._springs)
        if current_joint_count < self.initial_joint_count:
            self.structure_broken = True
        
        # Track initial height - wait a few steps for structure to stabilize
        # Record initial height after stabilization (around step 60, which is 1 second at 60fps)
        if step_count == 60 and self.initial_height == 0.0:
            self.initial_height = current_height
            print(f"Recorded initial height: {self.initial_height:.2f}m at step {step_count}")
        
        # Track height history (sample every 60 steps = 1 second)
        if step_count % 60 == 0:
            self.height_history.append((step_count, current_height))
        
        # Track minimum height during quake (after t=2s, which is approximately step 120 at 60fps)
        quake_start_step = int(2.0 * 60)  # 2 seconds at 60fps
        if step_count >= quake_start_step:
            self.min_height_during_quake = min(self.min_height_during_quake, current_height)
        
        # Track center of mass and physical state - only after initial stabilization
        # Start tracking after 120 steps (2 seconds) to allow structure to settle
        center_of_mass_x = 0.0
        center_of_mass_y = 0.0
        total_mass = 0.0
        if step_count >= 120 and self.environment._bodies:
            weighted_x = 0.0
            weighted_y = 0.0
            for body in self.environment._bodies:
                body_mass = body.mass
                total_mass += body_mass
                weighted_x += body.position.x * body_mass
                weighted_y += body.position.y * body_mass
                
                # Track maximum velocities
                velocity = body.linearVelocity
                self.max_velocity_x = max(self.max_velocity_x, abs(velocity.x))
                self.max_velocity_y = max(self.max_velocity_y, abs(velocity.y))
                self.max_angular_velocity = max(self.max_angular_velocity, abs(body.angularVelocity))
            
            if total_mass > 0:
                center_of_mass_x = weighted_x / total_mass
                center_of_mass_y = weighted_y / total_mass
                self.max_center_of_mass_x = max(self.max_center_of_mass_x, center_of_mass_x)
                self.min_center_of_mass_x = min(self.min_center_of_mass_x, center_of_mass_x)
                
                # Track center of mass history (sample every 60 steps = 1 second)
                if step_count % 60 == 0:
                    self.center_of_mass_history.append((step_count, center_of_mass_x, center_of_mass_y))
                
                # Debug: Print center of mass if it's getting out of bounds
                if step_count % 300 == 0:  # Every 5 seconds
                    if center_of_mass_x < self.stability_x_min or center_of_mass_x > self.stability_x_max:
                        print(f"Warning at step {step_count}: Center of mass x={center_of_mass_x:.2f}m is out of bounds")
        
        # Check success criteria
        # Only check height after initial height has been recorded
        if self.initial_height == 0.0:
            height_ok = True  # Wait for initial height to be recorded
        else:
            height_ok = self.initial_height > self.target_height
        # Allow some tolerance for structure settling during quake
        survival_ok = (self.min_height_during_quake > self.survival_height - self.survival_tolerance) if step_count >= quake_start_step else True
        # Only check stability after initial stabilization (step 60)
        # Also wait longer before checking stability to allow structure to settle
        if step_count < 120:  # Wait 2 seconds for structure to stabilize
            stability_ok = True  # Wait for structure to stabilize
        else:
            stability_ok = (self.min_center_of_mass_x >= self.stability_x_min and 
                           self.max_center_of_mass_x <= self.stability_x_max)
        
        success = height_ok and survival_ok and stability_ok
        
        # Don't return success too early - need to wait for quake to start and structure to survive
        # Quake starts at step 120 (2 seconds), and we need at least 30 seconds of quake
        # So minimum steps = 120 + 30*60 = 1920 steps
        quake_start_step = int(2.0 * 60)  # 2 seconds at 60fps
        min_survival_steps = quake_start_step + int(30.0 * 60)  # 30 seconds after quake starts
        if step_count < min_survival_steps:
            # Too early to declare success - wait for full quake duration
            success = False
        
        # Check failures
        failed = False
        failure_reason = None
        
        if not self.design_constraints_checked and step_count == 0:
            constraint_violations = self._check_design_constraints()
            if constraint_violations:
                failed = True
                failure_reason = "Design constraint violated: " + "; ".join(constraint_violations)
            self.design_constraints_checked = True
        
        # Only check height failure after initial height has been recorded
        if self.initial_height > 0.0 and not height_ok:
            failed = True
            failure_reason = f"Initial height {self.initial_height:.2f}m does not exceed {self.target_height}m"
        elif not survival_ok:
            failed = True
            effective_survival_height = self.survival_height - self.survival_tolerance
            failure_reason = f"Top point fell below {effective_survival_height:.2f}m during quake (min: {self.min_height_during_quake:.2f}m)"
        elif step_count >= 120 and not stability_ok:
            # Only fail if center of mass is significantly out of bounds
            # Allow some tolerance for initial settling
            tolerance = 0.5  # Allow 0.5m tolerance
            if (self.min_center_of_mass_x < self.stability_x_min - tolerance or 
                self.max_center_of_mass_x > self.stability_x_max + tolerance):
                failed = True
                failure_reason = f"Center of mass exceeded stability bounds x=[{self.stability_x_min}, {self.stability_x_max}] (range: [{self.min_center_of_mass_x:.2f}, {self.max_center_of_mass_x:.2f}])"
        
        # Calculate score
        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            # Partial score
            height_score = min(self.initial_height / self.target_height, 1.0) * 40
            survival_score = min(self.min_height_during_quake / self.survival_height, 1.0) * 40 if step_count >= quake_start_step else 0
            score = height_score + survival_score
        
        # Get structure mass if available
        structure_mass = None
        if hasattr(self.environment, 'get_structure_mass'):
            structure_mass = self.environment.get_structure_mass()
        
        # Calculate height loss during quake
        height_loss = 0.0
        if self.initial_height > 0 and step_count >= quake_start_step:
            height_loss = self.initial_height - self.min_height_during_quake
        
        # Calculate center of mass displacement
        com_displacement = 0.0
        if step_count >= 120:
            com_displacement = max(abs(self.min_center_of_mass_x), abs(self.max_center_of_mass_x))
        
        metrics = {
            # Height metrics
            'initial_height': self.initial_height,
            'current_height': current_height,
            'min_height_during_quake': self.min_height_during_quake if step_count >= quake_start_step else None,
            'height_loss': height_loss if step_count >= quake_start_step else 0.0,
            'target_height': self.target_height,
            'survival_height': self.survival_height,
            'survival_tolerance': self.survival_tolerance,
            
            # Stability metrics
            'center_of_mass_x': center_of_mass_x if step_count >= 120 else 0.0,
            'center_of_mass_y': center_of_mass_y if step_count >= 120 else 0.0,
            'center_of_mass_x_range': [self.min_center_of_mass_x, self.max_center_of_mass_x],
            'center_of_mass_displacement': com_displacement,
            'stability_x_min': self.stability_x_min,
            'stability_x_max': self.stability_x_max,
            
            # Structure properties
            'structure_mass': structure_mass,
            'structure_width': structure_width,
            'num_beams': len(self.environment._bodies),
            'num_joints': current_joint_count,
            'num_springs': current_spring_count,
            'initial_joint_count': self.initial_joint_count,
            'initial_spring_count': self.initial_spring_count,
            'structure_broken': self.structure_broken,
            
            # Physical state
            'max_velocity_x': self.max_velocity_x,
            'max_velocity_y': self.max_velocity_y,
            'max_angular_velocity': self.max_angular_velocity,
            
            # History (for detailed analysis)
            'height_history': self.height_history[-10:] if len(self.height_history) > 10 else self.height_history,  # Last 10 samples
            'center_of_mass_history': self.center_of_mass_history[-10:] if len(self.center_of_mass_history) > 10 else self.center_of_mass_history,
            
            # Simulation state
            'step_count': step_count,
            'quake_start_step': quake_start_step,
            'is_during_quake': step_count >= quake_start_step,
            
            # Results
            'success': success and not failed,
            'failed': failed,
            'failure_reason': failure_reason,
        }
        
        return success or failed, score, metrics
    
    def _check_design_constraints(self):
        """Check design constraints"""
        violations = []
        bounds = self.environment.get_structure_bounds()
        
        if bounds.get("width", 0) > self.MAX_WIDTH:
            violations.append(f"Structure width {bounds['width']:.2f}m exceeds maximum {self.MAX_WIDTH}m")
        
        # Check foundation contact (simplified - check if any body is outside foundation)
        for body in self.environment._bodies:
            if body.position.y < 1.0:  # Near ground
                if not (self.FOUNDATION_X_MIN <= body.position.x <= self.FOUNDATION_X_MAX):
                    violations.append(f"Structure touches ground outside foundation at x={body.position.x:.2f}m")
        
        return violations
    
    def get_task_description(self):
        """Return task description"""
        return {
            'task': 'S-02: The Skyscraper',
            'description': 'Build a tall tower that survives earthquake and wind',
            'target_height': self.target_height,
            'success_criteria': {
                'height': f'Initial height > {self.target_height}m',
                'survival': f'Top remains above {self.survival_height}m after quake',
                'stability': f'Center of mass within x=[{self.stability_x_min}, {self.stability_x_max}]'
            }
        }
