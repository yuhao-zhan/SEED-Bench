"""
D-06: The Catch task evaluation module (INSANE).

SUCCESS: ALL SEVEN balls caught (speed < 0.35 m/s) AND in TARGET x=[7,11], y=[0.5,5.5].
No beam in FOUR SWEEPER BANDS. No beam in forbidden zones.
PIT FAILURE: any ball at y<0.72 with speed>1.0 before caught = fail.
At most 9 beams, 10 kg. No joint broke (880 N).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


class Evaluator:
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self._caught_speed_threshold = 0.35  # m/s
        self._pit_y_threshold = 0.72  # ball below this = pit (near ground 0.5)
        self._pit_speed_threshold = 1.0  # if speed > this when in pit, fail
        self._ball_ever_in_pit_fast = False
        self._approach_x = 7.4  # increased leeway for high-speed mutated stages (allows more absorption time)
        self._ball_arrived = set()  # indices that have entered approach zone
        self._sequential_violation = False  # ball i arrived before ball j (j<i) was caught
        # UNIFIED target box (split zones would require complex routing)
        self._target_x_min = 7.0
        self._target_x_max = 11.0
        self._target_y_min = 0.5
        self._target_y_max = 5.5
        self._balls_caught = set()
        self._design_constraints_checked = False
        if environment is None:
            raise ValueError("Evaluator requires environment instance")
        self.MAX_STRUCTURE_MASS = getattr(environment, "MAX_STRUCTURE_MASS", 10.0)
        self.BUILD_ZONE_X_MIN = environment.BUILD_ZONE_X_MIN
        self.BUILD_ZONE_X_MAX = environment.BUILD_ZONE_X_MAX
        self.BUILD_ZONE_Y_MIN = environment.BUILD_ZONE_Y_MIN
        self.BUILD_ZONE_Y_MAX = environment.BUILD_ZONE_Y_MAX
        self.FORBIDDEN_ZONE_X_MIN = getattr(environment, "FORBIDDEN_ZONE_X_MIN", 8.5)
        self.FORBIDDEN_ZONE_X_MAX = getattr(environment, "FORBIDDEN_ZONE_X_MAX", 9.5)
        self.FORBIDDEN_ZONE_2_X_MIN = getattr(environment, "FORBIDDEN_ZONE_2_X_MIN", 7.35)
        self.FORBIDDEN_ZONE_2_X_MAX = getattr(environment, "FORBIDDEN_ZONE_2_X_MAX", 7.75)
        self.FORBIDDEN_ZONE_3_X_MIN = getattr(environment, "FORBIDDEN_ZONE_3_X_MIN", 7.78)
        self.FORBIDDEN_ZONE_3_X_MAX = getattr(environment, "FORBIDDEN_ZONE_3_X_MAX", 8.55)
        self.FORBIDDEN_ZONE_4_X_MIN = getattr(environment, "FORBIDDEN_ZONE_4_X_MIN", 10.0)
        self.FORBIDDEN_ZONE_4_X_MAX = getattr(environment, "FORBIDDEN_ZONE_4_X_MAX", 10.5)
        self.FORBIDDEN_ZONE_5_X_MIN = getattr(environment, "FORBIDDEN_ZONE_5_X_MIN", 7.18)
        self.FORBIDDEN_ZONE_5_X_MAX = getattr(environment, "FORBIDDEN_ZONE_5_X_MAX", 7.34)
        self.MAX_BEAM_COUNT = getattr(environment, "MAX_BEAM_COUNT", 9)
        self.SWEEPER_BAND_1_Y_MIN = getattr(environment, "SWEEPER_BAND_1_Y_MIN", 2.95)
        self.SWEEPER_BAND_1_Y_MAX = getattr(environment, "SWEEPER_BAND_1_Y_MAX", 3.55)
        self.SWEEPER_BAND_2_Y_MIN = getattr(environment, "SWEEPER_BAND_2_Y_MIN", 4.15)
        self.SWEEPER_BAND_2_Y_MAX = getattr(environment, "SWEEPER_BAND_2_Y_MAX", 4.75)
        self.SWEEPER_BAND_3_Y_MIN = getattr(environment, "SWEEPER_BAND_3_Y_MIN", 1.0)
        self.SWEEPER_BAND_3_Y_MAX = getattr(environment, "SWEEPER_BAND_3_Y_MAX", 1.5)
        self.SWEEPER_BAND_4_Y_MIN = getattr(environment, "SWEEPER_BAND_4_Y_MIN", 2.0)
        self.SWEEPER_BAND_4_Y_MAX = getattr(environment, "SWEEPER_BAND_4_Y_MAX", 2.5)
        tb = environment.get_terrain_bounds() if hasattr(environment, "get_terrain_bounds") else {}
        self._max_joint_force = tb.get("max_joint_force", 880.0)

    def evaluate(self, agent_body, step_count, max_steps):
        if self.environment is None:
            return True, 0.0, {"error": "Environment not available"}
        positions = self.environment.get_all_balls_positions() if hasattr(self.environment, "get_all_balls_positions") else [self.environment.get_ball_position()]
        velocities = self.environment.get_all_balls_velocities() if hasattr(self.environment, "get_all_balls_velocities") else [self.environment.get_ball_velocity()]
        if not positions or not velocities:
            return True, 0.0, {"error": "No balls found"}
        for i, (pos, vel) in enumerate(zip(positions, velocities)):
            if pos is None or vel is None:
                continue
            px, py = pos[0], pos[1]
            vx, vy = vel[0], vel[1]
            speed = (vx * vx + vy * vy) ** 0.5
            if py < self._pit_y_threshold and speed > self._pit_speed_threshold:
                self._ball_ever_in_pit_fast = True
            if px < self._approach_x and i not in self._ball_arrived:
                self._ball_arrived.add(i)
                for j in range(i):
                    if j in self._ball_arrived and j not in self._balls_caught:
                        self._sequential_violation = True
                        break
            in_target_box = (
                self._target_x_min <= px <= self._target_x_max
                and self._target_y_min <= py <= self._target_y_max
            )
            if speed < self._caught_speed_threshold and in_target_box:
                self._balls_caught.add(i)
        n_balls = len(positions)
        all_caught = len(self._balls_caught) >= n_balls and n_balls >= 7
        if not hasattr(self.environment, "get_all_balls_positions") or n_balls < 7:
            all_caught = False
        if n_balls >= 7 and len(self._balls_caught) < n_balls:
            all_caught = False
        if not self._design_constraints_checked and step_count == 0:
            violations = self._check_design_constraints()
            if violations:
                self._design_constraints_checked = True
                metrics = self._make_metrics(positions, velocities, step_count, False, True,
                    "Design constraint violated: " + "; ".join(violations))
                return True, 0.0, metrics
            self._design_constraints_checked = True
        structure_smashed = self.environment.is_structure_smashed()
        success = all_caught and not structure_smashed and not self._ball_ever_in_pit_fast and not self._sequential_violation
        failed = False
        failure_reason = None
        if self._ball_ever_in_pit_fast:
            failed = True
            failure_reason = "Pit failure: a ball reached y<0.72 with speed>1.0 m/s before being caught"
        elif self._sequential_violation:
            failed = True
            failure_reason = "Sequential constraint violated: a ball arrived at the catch zone before a previous ball was fully caught. Design must absorb each ball before the next arrives (ball-ball collisions can eject balls if they pile up)."
        elif structure_smashed:
            failed = True
            failure_reason = "Structure smashed: a joint broke (peak force exceeded limit or sustained high load — reduce impact forces and try again)"
        elif step_count >= max_steps - 1 and not all_caught:
            failed = True
            failure_reason = (
                f"Not all balls caught: each speed < {self._caught_speed_threshold} m/s in TARGET. "
                "Wind, penta forbidden zones, quad sweeper bands."
            )
        done = failed or success or step_count >= max_steps - 1
        score = 100.0 if success else (0.0 if failed else 0.0)
        metrics = self._make_metrics(positions, velocities, step_count, success, failed, failure_reason)
        return done, score, metrics

    def _check_design_constraints(self):
        violations = []
        if self.environment is None:
            return ["Environment not available"]
        n_joints = len(getattr(self.environment, "_joints", []))
        if n_joints < 1:
            violations.append(
                "Design must be anchored to ground: at least one beam must be connected via "
                "add_joint(body, None, anchor, 'rigid'). Unanchored structures are invalid."
            )
        mass = self.environment.get_structure_mass()
        if mass > self.MAX_STRUCTURE_MASS:
            violations.append(f"Structure mass {mass:.2f} kg exceeds maximum {self.MAX_STRUCTURE_MASS} kg")
        n_beams = len(self.environment._bodies)
        if n_beams > self.MAX_BEAM_COUNT:
            violations.append(f"Beam count {n_beams} exceeds maximum {self.MAX_BEAM_COUNT}")
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX and
                    self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX):
                violations.append(
                    f"Beam at ({x:.2f}, {y:.2f}) is outside build zone "
                    f"x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], "
                    f"y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]"
                )
            if self.FORBIDDEN_ZONE_X_MIN <= x <= self.FORBIDDEN_ZONE_X_MAX:
                violations.append(
                    f"Beam center at ({x:.2f}, {y:.2f}) is inside FORBIDDEN ZONE x=[{self.FORBIDDEN_ZONE_X_MIN}, {self.FORBIDDEN_ZONE_X_MAX}]"
                )
            if self.FORBIDDEN_ZONE_2_X_MIN <= x <= self.FORBIDDEN_ZONE_2_X_MAX:
                violations.append(
                    f"Beam center at ({x:.2f}, {y:.2f}) is inside FORBIDDEN ZONE 2 x=[{self.FORBIDDEN_ZONE_2_X_MIN}, {self.FORBIDDEN_ZONE_2_X_MAX}]"
                )
            if self.FORBIDDEN_ZONE_3_X_MIN <= x <= self.FORBIDDEN_ZONE_3_X_MAX:
                violations.append(
                    f"Beam center at ({x:.2f}, {y:.2f}) is inside FORBIDDEN ZONE 3 x=[{self.FORBIDDEN_ZONE_3_X_MIN}, {self.FORBIDDEN_ZONE_3_X_MAX}]"
                )
            if self.FORBIDDEN_ZONE_4_X_MIN <= x <= self.FORBIDDEN_ZONE_4_X_MAX:
                violations.append(
                    f"Beam center at ({x:.2f}, {y:.2f}) is inside FORBIDDEN ZONE 4 x=[{self.FORBIDDEN_ZONE_4_X_MIN}, {self.FORBIDDEN_ZONE_4_X_MAX}]"
                )
            if self.FORBIDDEN_ZONE_5_X_MIN <= x <= self.FORBIDDEN_ZONE_5_X_MAX:
                violations.append(
                    f"Beam center at ({x:.2f}, {y:.2f}) is inside FORBIDDEN ZONE 5 x=[{self.FORBIDDEN_ZONE_5_X_MIN}, {self.FORBIDDEN_ZONE_5_X_MAX}]"
                )
            if self.SWEEPER_BAND_1_Y_MIN <= y <= self.SWEEPER_BAND_1_Y_MAX:
                violations.append(
                    f"Beam center at ({x:.2f}, {y:.2f}) is inside SWEEPER BAND 1 y=[{self.SWEEPER_BAND_1_Y_MIN}, {self.SWEEPER_BAND_1_Y_MAX}]"
                )
            if self.SWEEPER_BAND_2_Y_MIN <= y <= self.SWEEPER_BAND_2_Y_MAX:
                violations.append(
                    f"Beam center at ({x:.2f}, {y:.2f}) is inside SWEEPER BAND 2 y=[{self.SWEEPER_BAND_2_Y_MIN}, {self.SWEEPER_BAND_2_Y_MAX}]"
                )
            if self.SWEEPER_BAND_3_Y_MIN <= y <= self.SWEEPER_BAND_3_Y_MAX:
                violations.append(
                    f"Beam center at ({x:.2f}, {y:.2f}) is inside SWEEPER BAND 3 y=[{self.SWEEPER_BAND_3_Y_MIN}, {self.SWEEPER_BAND_3_Y_MAX}]"
                )
            if self.SWEEPER_BAND_4_Y_MIN <= y <= self.SWEEPER_BAND_4_Y_MAX:
                violations.append(
                    f"Beam center at ({x:.2f}, {y:.2f}) is inside SWEEPER BAND 4 y=[{self.SWEEPER_BAND_4_Y_MIN}, {self.SWEEPER_BAND_4_Y_MAX}]"
                )
        return violations

    def _make_metrics(self, positions, velocities, step_count, success=False, failed=False, failure_reason=None):
        if not isinstance(positions, list):
            positions = [positions] if positions else [(0, 0)]
        if not isinstance(velocities, list):
            velocities = [velocities] if velocities else [(0, 0)]
        # Primary ball (ball 1) for backward-compat keys
        pos = positions[0] if positions else (0, 0)
        vel = velocities[0] if velocities else (0, 0)
        px, py = pos[0], pos[1]
        vx, vy = vel[0], vel[1]
        speed = (vx * vx + vy * vy) ** 0.5
        in_target = (
            self._target_x_min <= px <= self._target_x_max and
            self._target_y_min <= py <= self._target_y_max
        ) if pos else False
        all_caught = (
            hasattr(self.environment, "get_all_balls_positions") and len(positions) >= 7 and
            len(self._balls_caught) >= len(positions)
        )
        uncaptured_positions = []
        if not all_caught and positions:
            for i in range(len(positions)):
                if i not in self._balls_caught and i < len(positions):
                    pos_i = positions[i]
                    if pos_i:
                        uncaptured_positions.append((i + 1, float(pos_i[0]), float(pos_i[1])))
        structure_mass = self.environment.get_structure_mass()
        mass_budget_used = (structure_mass / self.MAX_STRUCTURE_MASS * 100) if self.MAX_STRUCTURE_MASS > 0 else 0
        terrain = self.environment.get_terrain_bounds() if hasattr(self.environment, "get_terrain_bounds") else {}
        max_joint_force = terrain.get("max_joint_force", 880.0)
        n_beams = len(getattr(self.environment, "_bodies", []))
        return {
            "ball_x": px, "ball_y": py,
            "ball_vx": vx, "ball_vy": vy, "ball_speed": speed,
            "success": success, "failed": failed, "failure_reason": failure_reason,
            "step_count": step_count,
            "structure_mass": structure_mass,
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "mass_budget_used_pct": mass_budget_used,
            "structure_smashed": self.environment.is_structure_smashed(),
            "ball_caught": all_caught,
            "ball_in_catch_zone": in_target,
            "joint_count": len(self.environment._joints),
            "beam_count": n_beams,
            "max_joint_force_limit": max_joint_force,
            "ball_speed_vs_threshold": speed - self._caught_speed_threshold,
            "balls_caught_count": len(self._balls_caught),
            "balls_required_count": len(positions),
            "uncaptured_positions": uncaptured_positions if uncaptured_positions else None,
            "pit_failure": getattr(self, "_ball_ever_in_pit_fast", False),
            "sequential_violation": getattr(self, "_sequential_violation", False),
        }

    def get_task_description(self):
        return {
            "task": "D-06: The Catch (Essential)",
            "description": "Catch SEVEN balls; deflector cooperation; ball-ball coupling; sequential order; max 9 beams, 10 kg",
            "success_criteria": {"primary": "All balls speed<0.35 m/s in target; no beam in 4 sweeper bands or 5 forbidden zones; no pit failure; structure intact", "failure": "Pit failure, structure smashed, beam in sweeper/forbidden zones, or not all balls caught"},
            "evaluation": {"score_range": "0-100", "success_score": 100, "failure_score": 0},
        }
