"""
F-01: The Dam task evaluation module
Defines task objectives and success criteria. Failure: leakage rate above the configured limit
(default 0.10%); runtime failure if beam-to-beam joints break. Design checks include mass cap,
beam count range, zero floor anchors, build strips, underflow, max beam width/height, joint cap,
vertical-band coverage, span, connectivity, and strip occupancy (middle/right).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


class Evaluator:
    """
    Evaluation system for F-01: The Dam (extreme variant).
    Success: leakage rate <= configured MAX_LEAKAGE_RATE (default 0.10%); no broken beam-to-beam joints.
    Design: mass/beam/joint/strip/band/span/connectivity rules from the environment; leak scoring uses
    the moving wall left edge (half-leak band 0.5 m upstream) or fallback x=14.0 m.
    """

    MAX_LEAKAGE_RATE = 0.001  # 0.10% — moving wall, debris, earthquake, min 3 beams per vertical band

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.initial_joint_count = 0
        self.initial_beam_to_beam_joint_count = 0
        self.structure_broken = False
        self.design_constraints_checked = False

        if not environment:
            raise ValueError("Evaluator requires environment instance")
        env_class = type(environment)
        self.MAX_LEAKAGE_RATE = getattr(environment, 'MAX_LEAKAGE_RATE', 0.001)
        # F-01 defaults: 380 kg, 0 anchors, 10–18 beams, right strip ≤2, 15 joints, build y max 7.5
        self.MAX_STRUCTURE_MASS = getattr(environment, 'MAX_STRUCTURE_MASS', getattr(env_class, 'MAX_STRUCTURE_MASS', 380.0))
        self.MAX_TERRAIN_ANCHORS = getattr(environment, 'MAX_TERRAIN_ANCHORS', getattr(env_class, 'MAX_TERRAIN_ANCHORS', 0))
        self.MAX_BEAM_COUNT = getattr(environment, 'MAX_BEAM_COUNT', getattr(env_class, 'MAX_BEAM_COUNT', 18))
        self.MIN_BEAM_COUNT = getattr(environment, 'MIN_BEAM_COUNT', getattr(env_class, 'MIN_BEAM_COUNT', 10))
        self.MAX_BEAMS_RIGHT_STRIP = getattr(environment, 'MAX_BEAMS_RIGHT_STRIP', getattr(env_class, 'MAX_BEAMS_RIGHT_STRIP', 2))
        self.MAX_BEAMS_MIDDLE_STRIP = getattr(environment, 'MAX_BEAMS_MIDDLE_STRIP', getattr(env_class, 'MAX_BEAMS_MIDDLE_STRIP', 1))
        # Three disjoint strips: left, middle (bridge), right
        self.BUILD_ZONE_LEFT_X_MIN = getattr(environment, 'BUILD_ZONE_LEFT_X_MIN', 12.4)
        self.BUILD_ZONE_LEFT_X_MAX = getattr(environment, 'BUILD_ZONE_LEFT_X_MAX', 12.6)
        self.BUILD_ZONE_MIDDLE_X_MIN = getattr(environment, 'BUILD_ZONE_MIDDLE_X_MIN', 12.9)
        self.BUILD_ZONE_MIDDLE_X_MAX = getattr(environment, 'BUILD_ZONE_MIDDLE_X_MAX', 13.1)
        self.BUILD_ZONE_RIGHT_X_MIN = getattr(environment, 'BUILD_ZONE_RIGHT_X_MIN', 13.4)
        self.BUILD_ZONE_RIGHT_X_MAX = getattr(environment, 'BUILD_ZONE_RIGHT_X_MAX', 13.6)
        # Defaults match Sandbox strip union [12.4, 13.6] when attrs are missing
        self.BUILD_ZONE_X_MIN = getattr(environment, 'BUILD_ZONE_X_MIN', 12.4)
        self.BUILD_ZONE_X_MAX = getattr(environment, 'BUILD_ZONE_X_MAX', 13.6)
        self.BUILD_ZONE_Y_MIN = getattr(environment, 'BUILD_ZONE_Y_MIN', 0.0)
        self.BUILD_ZONE_Y_MAX = getattr(environment, 'BUILD_ZONE_Y_MAX', 7.5)
        self.MIN_BEAM_BOTTOM_Y = getattr(environment, 'MIN_BEAM_BOTTOM_Y', 0.5)
        self.MAX_JOINT_COUNT = getattr(environment, 'MAX_JOINT_COUNT', getattr(env_class, 'MAX_JOINT_COUNT', 15))

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate dam performance. agent_body is not used (dam is multiple beams).
        Returns: (done, score, metrics). We run until max_steps then evaluate leakage.
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        # Design constraints check only at step 0
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
            terrain_joints = self.environment.get_terrain_joint_count() if hasattr(self.environment, 'get_terrain_joint_count') else 0
            self.initial_beam_to_beam_joint_count = self.initial_joint_count - terrain_joints

        # Structure integrity
        current_joint_count = len(self.environment._joints)
        terrain_joints = self.environment.get_terrain_joint_count() if hasattr(self.environment, 'get_terrain_joint_count') else 0
        current_beam_to_beam_joint_count = current_joint_count - terrain_joints
        if current_beam_to_beam_joint_count < self.initial_beam_to_beam_joint_count:
            self.structure_broken = True

        # Only decide success/failure and score when we have run long enough
        done = step_count >= max_steps
        if not done:
            metrics = self._collect_metrics(step_count, success=False, failed=False, failure_reason=None)
            return False, 0.0, metrics

        initial_count = self.environment.get_initial_particle_count()
        leaked_count = self.environment.get_leaked_particle_count()
        leakage_rate = (leaked_count / initial_count) if initial_count > 0 else 0.0

        failed = False
        failure_reason = None

        if leakage_rate > self.MAX_LEAKAGE_RATE:
            failed = True
            limit_pct = self.MAX_LEAKAGE_RATE * 100
            failure_reason = f"Leakage rate {leakage_rate * 100:.1f}% exceeds {limit_pct:.2f}% limit"

        if self.structure_broken:
            failed = True
            failure_reason = (failure_reason or "") + ("; " if failure_reason else "") + "Structure integrity lost (joints broke)"

        success = (leakage_rate <= self.MAX_LEAKAGE_RATE) and not self.structure_broken and not failed
        # Binary scoring: at horizon, outcome is success vs failure (partial tier was unreachable).
        score = 100.0 if success else 0.0

        metrics = self._collect_metrics(
            step_count,
            success=success,
            failed=failed,
            failure_reason=failure_reason,
            initial_count=initial_count,
            leaked_count=leaked_count,
            leakage_rate=leakage_rate,
        )
        return True, score, metrics

    def _collect_metrics(self, step_count, success=False, failed=False, failure_reason=None,
                         initial_count=None, leaked_count=None, leakage_rate=None):
        if initial_count is None:
            initial_count = self.environment.get_initial_particle_count()
        if leaked_count is None:
            leaked_count = self.environment.get_leaked_particle_count()
        if leakage_rate is None and initial_count > 0:
            leakage_rate = leaked_count / initial_count
        elif leakage_rate is None:
            leakage_rate = 0.0

        current_total = self.environment.get_particle_count()
        retained_count = initial_count - leaked_count
        containment_percent = (1.0 - leakage_rate) * 100.0 if initial_count > 0 else 100.0
        beam_count = len(self.environment._bodies)

        return {
            "step_count": step_count,
            "initial_particle_count": initial_count,
            "leaked_particle_count": leaked_count,
            "leakage_rate": leakage_rate,
            "leakage_rate_percent": leakage_rate * 100.0,
            "leakage_limit_percent": self.MAX_LEAKAGE_RATE * 100.0,
            "retained_particle_count": retained_count,
            "containment_percent": containment_percent,
            "current_particle_count": current_total,
            "beam_count": beam_count,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "structure_mass": self.environment.get_structure_mass(),
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "structure_broken": self.structure_broken,
            "joint_count": len(self.environment._joints),
            "terrain_joint_count": self.environment.get_terrain_joint_count() if hasattr(self.environment, 'get_terrain_joint_count') else 0,
            "max_beam_count": self.MAX_BEAM_COUNT,
        }

    def _check_design_constraints(self):
        violations = []
        if not self.environment:
            return ["Environment not available"]
        self.MIN_BEAM_BOTTOM_Y = getattr(self.environment, 'MIN_BEAM_BOTTOM_Y', 0.5)
        self.MAX_BEAM_HEIGHT = getattr(self.environment, 'MAX_BEAM_HEIGHT', 1.5)
        self.MAX_BEAM_WIDTH = getattr(self.environment, 'MAX_BEAM_WIDTH', 0.6)
        structure_mass = self.environment.get_structure_mass()
        if structure_mass > self.MAX_STRUCTURE_MASS:
            violations.append(f"Structure mass {structure_mass:.2f} kg exceeds maximum {self.MAX_STRUCTURE_MASS} kg")
        terrain_joints = self.environment.get_terrain_joint_count() if hasattr(self.environment, 'get_terrain_joint_count') else 0
        if terrain_joints > self.MAX_TERRAIN_ANCHORS:
            violations.append(
                f"Terrain anchors {terrain_joints} exceeds maximum {self.MAX_TERRAIN_ANCHORS} "
                + ("(no floor anchors allowed — dam must be free-standing)" if self.MAX_TERRAIN_ANCHORS == 0 else "(only floor anchors allowed)")
            )
        beam_count = len(self.environment._bodies)
        if beam_count > self.MAX_BEAM_COUNT:
            violations.append(f"Beam count {beam_count} exceeds maximum {self.MAX_BEAM_COUNT}")
        if beam_count < self.MIN_BEAM_COUNT:
            violations.append(f"Beam count {beam_count} is below minimum {self.MIN_BEAM_COUNT}")
        # MIN BEAMS PER VERTICAL BAND: at least 3 beams per band; bands derived from environment
        y_min = getattr(self.environment, 'MIN_BEAM_BOTTOM_Y', 0.5)
        y_max = getattr(self.environment, 'BUILD_ZONE_Y_MAX', 7.5)
        band_limits = [(y_min, 2.5), (2.5, 5.0), (5.0, y_max)]
        min_per_band = getattr(self.environment, 'MIN_BEAMS_PER_BAND', 3)
        for y_lo, y_hi in band_limits:
            n_in_band = sum(1 for b in self.environment._bodies
                           if y_lo <= b.position.y <= y_hi)
            if n_in_band < min_per_band:
                violations.append(
                    f"Vertical band y=[{y_lo}, {y_hi}] has {n_in_band} beam(s); at least {min_per_band} beams required in each band (even vertical distribution)"
                )
        right_strip_count = sum(1 for b in self.environment._bodies
                               if self.BUILD_ZONE_RIGHT_X_MIN <= b.position.x <= self.BUILD_ZONE_RIGHT_X_MAX)
        if right_strip_count > self.MAX_BEAMS_RIGHT_STRIP:
            violations.append(
                f"Right strip has {right_strip_count} beams; at most {self.MAX_BEAMS_RIGHT_STRIP} beams allowed in the right strip (asymmetric constraint)"
            )
        middle_strip_count = sum(1 for b in self.environment._bodies
                                 if self.BUILD_ZONE_MIDDLE_X_MIN <= b.position.x <= self.BUILD_ZONE_MIDDLE_X_MAX)
        if middle_strip_count > self.MAX_BEAMS_MIDDLE_STRIP:
            violations.append(
                f"Middle strip has {middle_strip_count} beams; at most {self.MAX_BEAMS_MIDDLE_STRIP} beam(s) allowed in the middle strip (bridge constraint)"
            )
        if middle_strip_count < 1:
            violations.append(
                f"Dam must use the middle strip: at least one beam center in middle strip x=[{self.BUILD_ZONE_MIDDLE_X_MIN}, {self.BUILD_ZONE_MIDDLE_X_MAX}] (bridge required for valid topology)"
            )
        beam_to_beam_joints = len(self.environment._joints) - terrain_joints
        if beam_to_beam_joints > self.MAX_JOINT_COUNT:
            violations.append(
                f"Beam-to-beam joint count {beam_to_beam_joints} exceeds maximum {self.MAX_JOINT_COUNT} (fewer welds = weaker structure constraint)"
            )
        bodies_set = set(self.environment._bodies)
        floor_body = self.environment._terrain_bodies.get("floor") if hasattr(self.environment, '_terrain_bodies') else None
        # ONE CONNECTED COMPONENT: every beam must be reachable from every other via beam-to-beam joints (no isolated sub-structures)
        if len(self.environment._bodies) > 0:
            # Build adjacency: beam -> set of beams connected by beam-to-beam joint
            adj = {b: set() for b in self.environment._bodies}
            for joint in self.environment._joints:
                a, b = joint.bodyA, joint.bodyB
                if a in bodies_set and b in bodies_set and b != floor_body and a != floor_body:
                    adj[a].add(b)
                    adj[b].add(a)
            from collections import deque
            start = next(iter(self.environment._bodies))
            visited = set()
            q = deque([start])
            visited.add(start)
            while q:
                u = q.popleft()
                for v in adj[u]:
                    if v not in visited:
                        visited.add(v)
                        q.append(v)
            if len(visited) != len(self.environment._bodies):
                violations.append(
                    "Dam must form one connected structure: every beam must be connected to every other via beam-to-beam joints (no separate columns or isolated beams)"
                )
        # SPAN: at least one beam in left strip and one in right strip
        left_count = sum(1 for b in self.environment._bodies
                        if self.BUILD_ZONE_LEFT_X_MIN <= b.position.x <= self.BUILD_ZONE_LEFT_X_MAX)
        right_count = sum(1 for b in self.environment._bodies
                         if self.BUILD_ZONE_RIGHT_X_MIN <= b.position.x <= self.BUILD_ZONE_RIGHT_X_MAX)
        if left_count < 1 or right_count < 1:
            violations.append(
                f"Dam must span the gate: at least one beam center in left strip x=[{self.BUILD_ZONE_LEFT_X_MIN}, {self.BUILD_ZONE_LEFT_X_MAX}] and at least one in right strip x=[{self.BUILD_ZONE_RIGHT_X_MIN}, {self.BUILD_ZONE_RIGHT_X_MAX}]"
            )
        # Build zones and mandatory underflow gap (left OR middle OR right)
        # For underflow, use world-space polygon vertices so rotated beams are checked correctly.
        def _world_bottom_y(body):
            try:
                mins = []
                for fx in getattr(body, "fixtures", []):
                    shape = getattr(fx, "shape", None)
                    verts = getattr(shape, "vertices", None)
                    if verts:
                        for v in verts:
                            wv = body.GetWorldPoint(v)
                            mins.append(float(wv[1]))
                if mins:
                    return min(mins)
            except Exception:
                pass
            return None

        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            in_left = self.BUILD_ZONE_LEFT_X_MIN <= x <= self.BUILD_ZONE_LEFT_X_MAX
            in_middle = self.BUILD_ZONE_MIDDLE_X_MIN <= x <= self.BUILD_ZONE_MIDDLE_X_MAX
            in_right = self.BUILD_ZONE_RIGHT_X_MIN <= x <= self.BUILD_ZONE_RIGHT_X_MAX
            in_y = self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX
            if not ((in_left or in_middle or in_right) and in_y):
                violations.append(
                    f"Beam at ({x:.2f}, {y:.2f}) is outside build zones "
                    f"(left x=[{self.BUILD_ZONE_LEFT_X_MIN}, {self.BUILD_ZONE_LEFT_X_MAX}], middle x=[{self.BUILD_ZONE_MIDDLE_X_MIN}, {self.BUILD_ZONE_MIDDLE_X_MAX}], or right x=[{self.BUILD_ZONE_RIGHT_X_MIN}, {self.BUILD_ZONE_RIGHT_X_MAX}], y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}])"
                )
            try:
                if body.fixtures:
                    shape = body.fixtures[0].shape
                    hx, hy = None, None
                    try:
                        if hasattr(shape, 'box'):
                            hx, hy = shape.box
                    except Exception:
                        pass
                    if hx is None and getattr(shape, 'vertices', None):
                        verts = shape.vertices
                        if len(verts) >= 2:
                            hx = max(abs(v[0]) for v in verts)
                            hy = max(abs(v[1]) for v in verts)
                    if hx is not None and hy is not None:
                        bottom = _world_bottom_y(body)
                        if bottom is None:
                            bottom = body.position.y - hy
                        if bottom < self.MIN_BEAM_BOTTOM_Y:
                            violations.append(
                                f"Beam at ({x:.2f}, {y:.2f}) extends below y={self.MIN_BEAM_BOTTOM_Y} (bottom={bottom:.2f}); mandatory underflow gap required"
                            )
                        beam_height = 2.0 * hy
                        beam_width = 2.0 * hx
                        if beam_height > self.MAX_BEAM_HEIGHT + 1e-6:
                            violations.append(
                                f"Beam at ({x:.2f}, {y:.2f}) has height {beam_height:.2f} m; maximum beam height is {self.MAX_BEAM_HEIGHT} m (tall beams break under surge)"
                            )
                        if beam_width > self.MAX_BEAM_WIDTH + 1e-6:
                            violations.append(
                                f"Beam at ({x:.2f}, {y:.2f}) has width {beam_width:.2f} m; maximum beam width is {self.MAX_BEAM_WIDTH} m"
                            )
            except (IndexError, TypeError, AttributeError):
                pass
        # Cross-joints ARE allowed — one connected component spanning both strips requires at least one cross-joint
        return violations

    def get_task_description(self):
        """For display/API; uses env-derived limits. Agent-facing prompt comes from task TASK_PROMPT + stage updates (stages.update_*_for_visible_changes)."""
        limit_pct = self.MAX_LEAKAGE_RATE * 100
        return {
            "task": "F-01: The Dam (extreme)",
            "description": f"Design a dam to block water particles; leakage rate must not exceed {limit_pct:.2f}%",
            "terrain": self.terrain_bounds,
            "success_criteria": {
                "primary": f"Leakage rate <= {limit_pct:.2f}%",
                "secondary": "Dam structure remains intact (no broken joints)",
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
