"""
F-05: The Boat task evaluation module
Failure: cargo crosses the loss plane, boat roll limit exceeded, or joints break.
"""
import sys
import os
import math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


class Evaluator:
    """
    Evaluation for F-05: The Boat.
    Success: no cargo below the loss plane (after grace), peak roll within limit, structure intact.
    Failure: loss-plane violation, capsize, or broken welds.
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.initial_joint_count = None
        self.structure_broken = False
        self.design_constraints_checked = False

        if not environment:
            raise ValueError("Evaluator requires environment instance")
        env_class = type(environment)
        self.MAX_STRUCTURE_MASS = getattr(environment, 'MAX_STRUCTURE_MASS', getattr(env_class, 'MAX_STRUCTURE_MASS', 60.0))
        self.BUILD_ZONE_X_MIN = getattr(environment, 'BUILD_ZONE_X_MIN', getattr(env_class, 'BUILD_ZONE_X_MIN', 12.0))
        self.BUILD_ZONE_X_MAX = getattr(environment, 'BUILD_ZONE_X_MAX', getattr(env_class, 'BUILD_ZONE_X_MAX', 18.0))
        self.BUILD_ZONE_Y_MIN = getattr(environment, 'BUILD_ZONE_Y_MIN', getattr(env_class, 'BUILD_ZONE_Y_MIN', 2.0))
        self.BUILD_ZONE_Y_MAX = getattr(environment, 'BUILD_ZONE_Y_MAX', getattr(env_class, 'BUILD_ZONE_Y_MAX', 4.5))
        self.BOAT_MAX_ANGLE_RAD = getattr(environment, 'BOAT_MAX_ANGLE_RAD', math.radians(18.0))
        self.CARGO_WATER_Y = getattr(environment, 'CARGO_WATER_Y', 1.98)

    @staticmethod
    def _joint_world_anchor_xy(joint):
        """World (x, y) of weld anchor (midpoint of bodyA/bodyB world anchors), or (None, None)."""
        try:
            if hasattr(joint, "bodyA") and hasattr(joint, "bodyB") and joint.bodyA and joint.bodyB:
                if hasattr(joint, "anchorA") and hasattr(joint, "anchorB"):
                    wa = joint.bodyA.GetWorldPoint(joint.anchorA)
                    wb = joint.bodyB.GetWorldPoint(joint.anchorB)
                    return (float(wa.x + wb.x) * 0.5, float(wa.y + wb.y) * 0.5)
                p = joint.bodyA.GetWorldPoint(joint.anchorA)
                return float(p.x), float(p.y)
        except Exception:
            pass
        if hasattr(joint, "anchor"):
            a = joint.anchor
            if isinstance(a, (tuple, list)) and len(a) >= 2:
                return float(a[0]), float(a[1])
            if hasattr(a, "x") and hasattr(a, "y"):
                return float(a.x), float(a.y)
        return None, None

    @staticmethod
    def _beam_footprint_outside_build_zone(body, xmin, xmax, ymin, ymax):
        """
        True if any world-space vertex of a polygon fixture on the body lies outside the
        inclusive axis-aligned build zone (used for agent beams from add_beam).
        """
        for fixture in body.fixtures:
            shape = fixture.shape
            verts = getattr(shape, "vertices", None)
            if not verts:
                continue
            for v in verts:
                try:
                    w = body.GetWorldPoint(v)
                except (AttributeError, TypeError, ValueError):
                    continue
                wx, wy = float(w.x), float(w.y)
                if not (xmin <= wx <= xmax and ymin <= wy <= ymax):
                    return True, wx, wy
        return False, None, None

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate boat performance. Returns: (done, score, metrics).
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        # Run design checks on the first evaluate() call regardless of step_count so callers
        # that skip step 0 still enforce mass / build zone / anchor constraints.
        if not self.design_constraints_checked:
            violations = self._check_design_constraints()
            self.initial_joint_count = len(self.environment._joints)
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

        if self.initial_joint_count is None:
            self.initial_joint_count = len(self.environment._joints)

        current_joint_count = len(self.environment._joints)
        if current_joint_count < self.initial_joint_count:
            self.structure_broken = True

        done = step_count >= max_steps
        if not done:
            metrics = self._collect_metrics(step_count, success=False, failed=False, failure_reason=None)
            return False, 0.0, metrics

        cargo_in_water = self.environment.get_cargo_in_water_count()
        initial_cargo = self.environment.get_initial_cargo_count()
        boat_angle = self.environment.get_boat_angle()
        angle_deg = math.degrees(abs(boat_angle)) if boat_angle is not None else 0.0
        max_angle_deg = math.degrees(self.BOAT_MAX_ANGLE_RAD)

        peak_fn = getattr(self.environment, "get_peak_abs_boat_angle_rad", None)
        peak_abs_rad = float(peak_fn()) if callable(peak_fn) else (
            abs(float(boat_angle)) if boat_angle is not None else 0.0
        )
        peak_angle_deg = math.degrees(peak_abs_rad)

        ever_fn = getattr(self.environment, "get_cargo_ever_below_loss_plane", None)
        cargo_ever_lost = bool(ever_fn()) if callable(ever_fn) else (cargo_in_water > 0)

        failed = False
        failure_reason = None

        if cargo_ever_lost:
            failed = True
            failure_reason = (
                f"Cargo loss plane crossed at least once (center y < {self.CARGO_WATER_Y:.2f} m); "
                f"{cargo_in_water}/{initial_cargo} below plane at end"
            )

        if peak_abs_rad > self.BOAT_MAX_ANGLE_RAD:
            failed = True
            failure_reason = (failure_reason or "") + ("; " if failure_reason else "") + (
                f"Boat exceeded roll limit (peak |angle| {peak_angle_deg:.1f}° > {max_angle_deg:.0f}°)"
            )

        if self.structure_broken:
            failed = True
            failure_reason = (failure_reason or "") + ("; " if failure_reason else "") + "Structure integrity lost (joints broke)"

        success = not failed
        score = 100.0 if success else 0.0

        metrics = self._collect_metrics(
            step_count,
            success=success,
            failed=failed,
            failure_reason=failure_reason,
            cargo_in_water=cargo_in_water,
            initial_cargo=initial_cargo,
            boat_angle_rad=boat_angle,
            boat_angle_deg=angle_deg,
            boat_peak_angle_deg=peak_angle_deg,
            cargo_ever_below_loss_plane=cargo_ever_lost,
        )
        return True, score, metrics

    def _collect_metrics(self, step_count, success=False, failed=False, failure_reason=None,
                         cargo_in_water=None, initial_cargo=None, boat_angle_rad=None, boat_angle_deg=None,
                         boat_peak_angle_deg=None, cargo_ever_below_loss_plane=None):
        if cargo_in_water is None:
            cargo_in_water = self.environment.get_cargo_in_water_count()
        if initial_cargo is None:
            initial_cargo = self.environment.get_initial_cargo_count()
        if boat_angle_rad is None:
            boat_angle_rad = self.environment.get_boat_angle()
        if boat_angle_deg is None and boat_angle_rad is not None:
            boat_angle_deg = math.degrees(abs(boat_angle_rad))

        if boat_peak_angle_deg is None:
            peak_fn = getattr(self.environment, "get_peak_abs_boat_angle_rad", None)
            if callable(peak_fn):
                boat_peak_angle_deg = math.degrees(float(peak_fn()))
            elif boat_angle_rad is not None:
                boat_peak_angle_deg = math.degrees(abs(float(boat_angle_rad)))
            else:
                boat_peak_angle_deg = 0.0

        if cargo_ever_below_loss_plane is None:
            ever_fn = getattr(self.environment, "get_cargo_ever_below_loss_plane", None)
            cargo_ever_below_loss_plane = bool(ever_fn()) if callable(ever_fn) else False

        boat_pos = self.environment.get_boat_position() if hasattr(self.environment, 'get_boat_position') else None
        boat_x = boat_pos[0] if boat_pos else None
        boat_y = boat_pos[1] if boat_pos else None
        # Align with scorer: retention failure is *ever* below the loss plane, not end-state count only.
        if cargo_ever_below_loss_plane and initial_cargo is not None:
            cargo_retained = 0
            cargo_retained_ratio = 0.0
        else:
            cargo_retained = (initial_cargo - cargo_in_water) if initial_cargo is not None else None
            cargo_retained_ratio = (cargo_retained / initial_cargo) if (initial_cargo and initial_cargo > 0) else None

        return {
            "step_count": step_count,
            "initial_cargo_count": initial_cargo,
            "cargo_in_water": cargo_in_water,
            "cargo_retained": cargo_retained,
            "cargo_retained_ratio": cargo_retained_ratio,
            "cargo_water_y": self.CARGO_WATER_Y,
            "water_surface_y": float(getattr(self.environment, "WATER_SURFACE_Y", 2.0)),
            "cargo_ever_below_loss_plane": cargo_ever_below_loss_plane,
            "boat_angle_rad": boat_angle_rad,
            "boat_angle_deg": boat_angle_deg,
            "boat_peak_angle_deg": boat_peak_angle_deg,
            "boat_max_angle_deg": math.degrees(self.BOAT_MAX_ANGLE_RAD),
            "boat_x": boat_x,
            "boat_y": boat_y,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "structure_mass": self.environment.get_structure_mass(),
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "build_zone_x_min": self.BUILD_ZONE_X_MIN,
            "build_zone_x_max": self.BUILD_ZONE_X_MAX,
            "build_zone_y_min": self.BUILD_ZONE_Y_MIN,
            "build_zone_y_max": self.BUILD_ZONE_Y_MAX,
            "structure_broken": self.structure_broken,
            "joint_count": len(self.environment._joints),
        }

    def _check_design_constraints(self):
        violations = []
        if not self.environment:
            return ["Environment not available"]
        structure_mass = self.environment.get_structure_mass()
        if structure_mass > self.MAX_STRUCTURE_MASS:
            violations.append(f"Structure mass {structure_mass:.2f} kg exceeds maximum {self.MAX_STRUCTURE_MASS} kg")
        for body in self.environment._bodies:
            bad, wx, wy = self._beam_footprint_outside_build_zone(
                body,
                self.BUILD_ZONE_X_MIN,
                self.BUILD_ZONE_X_MAX,
                self.BUILD_ZONE_Y_MIN,
                self.BUILD_ZONE_Y_MAX,
            )
            if bad:
                violations.append(
                    f"Beam footprint extends outside build zone (e.g. vertex at ({wx:.2f}, {wy:.2f})); "
                    f"allowed x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], "
                    f"y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]"
                )
        for j in self.environment._joints:
            decl = getattr(j, "_f05_declared_anchor_world", None)
            if decl is not None and len(decl) >= 2:
                ax, ay = float(decl[0]), float(decl[1])
            else:
                ax, ay = self._joint_world_anchor_xy(j)
            if ax is None or ay is None:
                continue
            if not (self.BUILD_ZONE_X_MIN <= ax <= self.BUILD_ZONE_X_MAX and
                    self.BUILD_ZONE_Y_MIN <= ay <= self.BUILD_ZONE_Y_MAX):
                violations.append(
                    f"Joint anchor at ({ax:.2f}, {ay:.2f}) is outside build zone "
                    f"x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]"
                )
        return violations

    def get_task_description(self):
        """Structured task metadata; numerics follow the live environment (keep aligned with TASK_PROMPT + stages updates)."""
        max_angle_deg = math.degrees(self.BOAT_MAX_ANGLE_RAD)
        tertiary = "Structure remains intact (all welds survive the episode)"
        jmf = float(getattr(self.environment, "JOINT_MAX_FORCE", float("inf")))
        if jmf < float("inf"):
            tertiary = (
                "Welds can break when simulated per-weld reaction force or torque exceeds the numeric "
                "caps listed in Success Criteria (force cap and 0.4× force-cap torque limit)."
            )
        return {
            "task": "F-05: The Boat",
            "description": f"Keep cargo on boat in rough water; boat must not capsize (angle <= {max_angle_deg:.0f}°)",
            "terrain": self.terrain_bounds,
            "success_criteria": {
                "primary": (
                    f"No cargo below loss plane after the grace window (center y < {self.CARGO_WATER_Y:.2f} m; "
                    f"first {getattr(self.environment, '_cargo_loss_grace_steps', 120)} physics steps ignored for this rule)"
                ),
                "secondary": f"Boat peak |roll angle| <= {max_angle_deg:.0f}° for full episode",
                "tertiary": tertiary,
            },
            "evaluation": {"score_range": "0-100", "success_score": 100, "failure_score": 0},
        }
