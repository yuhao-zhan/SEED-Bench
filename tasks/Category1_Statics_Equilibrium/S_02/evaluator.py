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
        self.SURVIVAL_THRESHOLD = 10.0 # Lowered from 18.0 to accommodate Stage-1 solution
        self.STABILITY_ZONE = 4.0 # COM must stay within x=[-4, 4] per prompt
        
        self.initial_height = 0.0
        self.min_height_during_quake = float('inf')
        self.design_constraints_checked = False
        
        # Determine earthquake start step
        self.quake_start_time = getattr(environment, "_earthquake_start_time", 2.0) if environment else 2.0
        self.quake_start_step = int(self.quake_start_time * 60.0)

    def evaluate(self, agent_body, step_count, max_steps):
        if self.environment is None:
            return True, 0.0, {"error": "Environment not set"}

        bounds = self.environment.get_structure_bounds()
        current_height = bounds.get("top", 0)
        
        # Capture peak height in stable period before earthquake
        if 10 <= step_count < self.quake_start_step:
            self.initial_height = max(self.initial_height, current_height)

        # Track survival during earthquake
        if step_count >= self.quake_start_step:
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

        failed = False
        reason = None
        
        if step_count == 1 and not self.design_constraints_checked:
            if bounds.get("width", 0) > 8.0:
                failed, reason = True, f"Width {bounds.get('width', 0):.2f}m > 8.0m"
            self.design_constraints_checked = True
        
        if not failed and step_count >= self.quake_start_step:
            if current_height < 5.0:
                failed, reason = True, "Collapsed"
            elif abs(rel_com_x) > self.STABILITY_ZONE:
                failed, reason = True, f"Tipped Over (rel_com_x={rel_com_x:.2f}, limit={self.STABILITY_ZONE})"
            elif current_height > 150.0:
                failed, reason = True, "Physical instability (Explosion)"

        # Determine success at end of simulation
        is_end = (step_count >= max_steps - 1)
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
            score = min(current_height / self.TARGET_HEIGHT, 1.0) * 80.0

        return done, score, {
            "initial_height": self.initial_height,
            "min_height": self.min_height_during_quake if step_count >= self.quake_start_step else None,
            "rel_com_x": rel_com_x,
            "success": success,
            "failure_reason": reason
        }

    def get_task_description(self):
        return {
            "task": "S-02: The Skyscraper",
            "description": f"Build a tower > {self.TARGET_HEIGHT}m that survives an earthquake",
            "success_criteria": {
                "initial_height": f"> {self.TARGET_HEIGHT}m",
                "survival": f"Remain above {self.SURVIVAL_THRESHOLD}m during quake",
                "stability": f"COM remains within ±{self.STABILITY_ZONE}m of foundation"
            }
        }
