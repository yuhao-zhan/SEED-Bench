"""
F-04: The Filter task evaluation module (feedback-driven variant)
Three-way separation: small / medium / large. Zone boundaries not given; infer from feedback.
Failure: purity < MIN_PURITY, structure broken.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


class Evaluator:
    """
    Evaluation for F-04: Three-way Filter.
    Success: classification purity >= MIN_PURITY, structure intact.
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.initial_joint_count = 0
        self.structure_broken = False
        self.design_constraints_checked = False

        if not environment:
            raise ValueError("Evaluator requires environment instance")
        env_class = type(environment)
        self.MAX_STRUCTURE_MASS = getattr(environment, 'MAX_STRUCTURE_MASS', getattr(env_class, 'MAX_STRUCTURE_MASS', 500.0))
        self.MAX_BEAMS = getattr(environment, 'MAX_BEAMS', getattr(env_class, 'MAX_BEAMS', 999))
        self.BUILD_ZONE_X_MIN = getattr(environment, 'BUILD_ZONE_X_MIN', getattr(env_class, 'BUILD_ZONE_X_MIN', 2.0))
        self.BUILD_ZONE_X_MAX = getattr(environment, 'BUILD_ZONE_X_MAX', getattr(env_class, 'BUILD_ZONE_X_MAX', 12.0))
        self.BUILD_ZONE_Y_MIN = getattr(environment, 'BUILD_ZONE_Y_MIN', getattr(env_class, 'BUILD_ZONE_Y_MIN', 1.0))
        self.BUILD_ZONE_Y_MAX = getattr(environment, 'BUILD_ZONE_Y_MAX', getattr(env_class, 'BUILD_ZONE_Y_MAX', 4.0))
        self.MIN_PURITY = getattr(environment, 'MIN_PURITY', getattr(env_class, 'MIN_PURITY', 0.40))

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate three-way filter. Returns: (done, score, metrics).
        Zero contamination: any large-in-small, small-in-large, or medium in wrong zone => fail.
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        if not self.design_constraints_checked and step_count == 0:
            violations = self._check_design_constraints()
            if violations:
                self.design_constraints_checked = True
                return True, 0.0, {
                    "success": False,
                    "failed": True,
                    "failure_reason": "Design constraint violated: " + "; ".join(violations),
                    "step_count": step_count,
                    "constraint_violations": violations,
                }
            self.design_constraints_checked = True
            self.initial_joint_count = len(self.environment._joints)

        current_joint_count = len(self.environment._joints)
        if current_joint_count < self.initial_joint_count:
            self.structure_broken = True

        done = step_count >= max_steps
        if not done:
            metrics = self._collect_metrics(step_count, success=False, failed=False, failure_reason=None)
            return False, 0.0, metrics

        purity = self.environment.get_classification_purity()
        initial_total = self.environment.get_initial_particle_count()
        small_in_small = self.environment.get_small_in_small_zone_count()
        medium_in_medium = self.environment.get_medium_in_medium_zone_count()
        large_in_large = self.environment.get_large_in_large_zone_count()
        contaminated = getattr(self.environment, 'has_contamination', lambda: False)()

        failed = False
        failure_reason = None

        if purity < self.MIN_PURITY:
            failed = True
            failure_reason = f"Classification purity {purity*100:.1f}% below {self.MIN_PURITY*100:.0f}% target"

        if self.structure_broken:
            failed = True
            failure_reason = (failure_reason or "") + ("; " if failure_reason else "") + "Structure integrity lost (joints broke)"

        success = (purity >= self.MIN_PURITY and not self.structure_broken and not failed)

        if success:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            score = max(0.0, 80.0 * (purity / self.MIN_PURITY))

        metrics = self._collect_metrics(
            step_count,
            success=success,
            failed=failed,
            failure_reason=failure_reason,
            purity=purity,
            initial_total=initial_total,
            small_in_small=small_in_small,
            medium_in_medium=medium_in_medium,
            large_in_large=large_in_large,
            contaminated=contaminated,
        )
        return True, score, metrics

    def _collect_metrics(self, step_count, success=False, failed=False, failure_reason=None,
                         purity=None, initial_total=None, small_in_small=None, medium_in_medium=None,
                         large_in_large=None, contaminated=None):
        if initial_total is None:
            initial_total = self.environment.get_initial_particle_count()
        if small_in_small is None:
            small_in_small = self.environment.get_small_in_small_zone_count()
        if medium_in_medium is None:
            medium_in_medium = getattr(self.environment, 'get_medium_in_medium_zone_count', lambda: 0)()
        if large_in_large is None:
            large_in_large = self.environment.get_large_in_large_zone_count()
        if purity is None:
            purity = self.environment.get_classification_purity()
        if contaminated is None:
            contaminated = getattr(self.environment, 'has_contamination', lambda: False)()

        small_above = self.environment.get_small_above_sieve_count()
        small_in_band = self.environment.get_small_in_sieve_band_count()
        large_below = self.environment.get_large_below_sieve_count()
        large_in_band = self.environment.get_large_in_sieve_band_count()
        large_in_small = getattr(self.environment, 'get_large_in_small_zone_count', lambda: 0)()
        small_in_large = getattr(self.environment, 'get_small_in_large_zone_count', lambda: 0)()
        medium_in_small = getattr(self.environment, 'get_medium_in_small_zone_count', lambda: 0)()
        medium_in_large = getattr(self.environment, 'get_medium_in_large_zone_count', lambda: 0)()

        return {
            "step_count": step_count,
            "initial_particle_count": initial_total,
            "small_in_small_zone": small_in_small,
            "medium_in_medium_zone": medium_in_medium,
            "large_in_large_zone": large_in_large,
            "small_above_sieve": small_above,
            "small_in_sieve_band": small_in_band,
            "large_below_sieve": large_below,
            "large_in_sieve_band": large_in_band,
            "large_in_small_zone": large_in_small,
            "small_in_large_zone": small_in_large,
            "medium_in_small_zone": medium_in_small,
            "medium_in_large_zone": medium_in_large,
            "classification_purity": purity,
            "purity_percent": purity * 100.0,
            "min_purity": self.MIN_PURITY,
            "min_purity_percent": self.MIN_PURITY * 100.0,
            "contaminated": contaminated,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "structure_mass": self.environment.get_structure_mass(),
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "structure_broken": self.structure_broken,
            "joint_count": len(self.environment._joints),
            "beam_count": len(self.environment._bodies),
            "max_beams": self.MAX_BEAMS,
        }

    def _check_design_constraints(self):
        violations = []
        if not self.environment:
            return ["Environment not available"]
        n_beams = len(self.environment._bodies)
        if n_beams > self.MAX_BEAMS:
            violations.append(f"Number of beams {n_beams} exceeds maximum {self.MAX_BEAMS}")
        structure_mass = self.environment.get_structure_mass()
        if structure_mass > self.MAX_STRUCTURE_MASS:
            violations.append(f"Structure mass {structure_mass:.2f} kg exceeds maximum {self.MAX_STRUCTURE_MASS} kg")
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX and
                    self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX):
                violations.append(
                    f"Beam at ({x:.2f}, {y:.2f}) is outside build zone "
                    f"x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]"
                )
        return violations

    def get_task_description(self):
        return {
            "task": "F-04: The Filter (Three-way)",
            "description": f"Separate small, medium, and large balls into three zones; purity >= {self.MIN_PURITY*100:.0f}%, structure intact",
            "terrain": self.terrain_bounds,
            "success_criteria": {
                "primary": f"Classification purity >= {self.MIN_PURITY*100:.0f}%",
                "secondary": "Structure remains intact",
            },
            "evaluation": {"score_range": "0-100", "success_score": 100, "failure_score": 0},
        }
