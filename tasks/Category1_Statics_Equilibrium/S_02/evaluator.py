"""
S-02: The Skyscraper task evaluation module
"""
import math

class Evaluator:
    """Evaluation system for S-02: The Skyscraper"""
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        
        self.TARGET_HEIGHT = 30.0
        self.SURVIVAL_THRESHOLD = 18.0
        self.STABILITY_ZONE = 10.0
        
        self.initial_height = 0.0
        self.min_height_during_quake = float('inf')
        self.min_survival_steps = int(32.0 * 60) 
        self.design_constraints_checked = False

    def evaluate(self, agent_body, step_count, max_steps):
        if self.environment is None:
            return True, 0.0, {"error": "Environment not set"}

        bounds = self.environment.get_structure_bounds()
        current_height = bounds.get("top", 0)
        
        # Robustly capture peak height in early stage
        if 10 <= step_count <= 100:
            self.initial_height = max(self.initial_height, current_height)

        # Track survival during earthquake (starts at step 120)
        if step_count >= 120:
            self.min_height_during_quake = min(self.min_height_during_quake, current_height)
            
        foundation_x = 0.0
        if "foundation" in self.environment._terrain_bodies:
            foundation_x = self.environment._terrain_bodies["foundation"].position.x
        
        # Relative Center of Mass (COM)
        rel_com_x = 0.0
        total_mass = 0.0
        import Box2D
        for body in self.environment._bodies:
            if body.type == Box2D.b2_dynamicBody:
                total_mass += body.mass
                rel_com_x += body.position.x * body.mass
        if total_mass > 0:
            rel_com_x = (rel_com_x / total_mass) - foundation_x

        # Check for catastrophic failure (Explosion or Total Collapse)
        failed = False
        reason = None
        
        if step_count == 1 and not self.design_constraints_checked:
            # Check width constraint (optional, depending on prompt)
            if bounds.get("width", 0) > 8.0:
                failed, reason = True, f"Width {bounds.get('width', 0):.2f}m > 8.0m"
            self.design_constraints_checked = True
        
        if not failed and step_count >= 120:
            if current_height < 5.0:
                failed, reason = True, "Collapsed"
            elif abs(rel_com_x) > self.STABILITY_ZONE:
                failed, reason = True, f"Tipped Over (rel_com_x={rel_com_x:.2f})"
            elif current_height > 150.0:
                failed, reason = True, "Physical instability (Explosion)"

        # Determine success at end of simulation
        is_end = (step_count >= self.min_survival_steps)
        success = False
        if is_end and not failed:
            if self.initial_height < self.TARGET_HEIGHT:
                failed, reason = True, f"Initial height {self.initial_height:.1f}m < {self.TARGET_HEIGHT}m"
            elif self.min_height_during_quake < self.SURVIVAL_THRESHOLD:
                failed, reason = True, f"Tower fell below survival line ({self.min_height_during_quake:.1f}m)"
            else:
                success = True

        done = failed or is_end
        score = 100.0 if success else 0.0
        if not done:
            score = min(current_height / self.TARGET_HEIGHT, 1.0) * 100.0

        return done, score, {
            "initial_height": self.initial_height,
            "min_height": self.min_height_during_quake if step_count >= 120 else None,
            "rel_com_x": rel_com_x,
            "success": success,
            "failure_reason": reason
        }

    def get_task_description(self):
        return {"task": "S-02 Skyscraper"}
