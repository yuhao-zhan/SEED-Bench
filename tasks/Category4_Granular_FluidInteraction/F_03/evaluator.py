"""
F-03: The Excavator — evaluation module.
Per user spec: base at (-2,0), at least 2 DOF (Arm + Bucket); at least 15 particles in hopper within 40 s.
"""
import sys
import os
import math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.simulator import TIME_STEP, TARGET_FPS


class Evaluator:
    """
    Evaluation for F-03: The Excavator.
    Success: >= 15 particles in hopper, within 40 s, structure intact, base at (-2,0), >= 2 revolute joints.
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
        self.MAX_STRUCTURE_MASS = getattr(environment, 'MAX_STRUCTURE_MASS', getattr(env_class, 'MAX_STRUCTURE_MASS', 800.0))
        self.BUILD_ZONE_X_MIN = getattr(environment, 'BUILD_ZONE_X_MIN', getattr(env_class, 'BUILD_ZONE_X_MIN', -4.0))
        self.BUILD_ZONE_X_MAX = getattr(environment, 'BUILD_ZONE_X_MAX', getattr(env_class, 'BUILD_ZONE_X_MAX', 2.0))
        self.BUILD_ZONE_Y_MIN = getattr(environment, 'BUILD_ZONE_Y_MIN', getattr(env_class, 'BUILD_ZONE_Y_MIN', 0.0))
        self.BUILD_ZONE_Y_MAX = getattr(environment, 'BUILD_ZONE_Y_MAX', getattr(env_class, 'BUILD_ZONE_Y_MAX', 5.0))
        self.BASE_X = getattr(environment, 'BASE_X', getattr(env_class, 'BASE_X', -2.0))
        self.BASE_Y = getattr(environment, 'BASE_Y', getattr(env_class, 'BASE_Y', 0.0))
        self.MIN_PARTICLES_IN_HOPPER = getattr(environment, 'MIN_PARTICLES_IN_HOPPER', getattr(env_class, 'MIN_PARTICLES_IN_HOPPER', 15))
        self.MAX_TIME_SECONDS = getattr(environment, 'MAX_TIME_SECONDS', getattr(env_class, 'MAX_TIME_SECONDS', 40.0))
        self.MAX_STEPS = int(self.MAX_TIME_SECONDS * TARGET_FPS)

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate excavator: base at (-2,0), >= 2 DOF, >= 15 in hopper, within 40 s. Returns (done, score, metrics).
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        initial_count = self.environment.get_initial_particle_count()

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

        # Time limit: 40 seconds (use min of max_steps and MAX_STEPS)
        effective_max_steps = min(max_steps, self.MAX_STEPS)
        done = step_count >= effective_max_steps
        if not done:
            metrics = self._collect_metrics(step_count, success=False, failed=False, failure_reason=None, agent_body=agent_body)
            return False, 0.0, metrics

        in_hopper_count = self.environment.get_particles_in_hopper_count()
        collected_ratio = (in_hopper_count / initial_count) if initial_count > 0 else 0.0

        failed = False
        failure_reason = None

        if in_hopper_count < self.MIN_PARTICLES_IN_HOPPER:
            failure_reason = f"Deposited {in_hopper_count}/{initial_count} particles (need at least {self.MIN_PARTICLES_IN_HOPPER} in hopper)"

        if self.structure_broken:
            failed = True
            failure_reason = (failure_reason or "") + ("; " if failure_reason else "") + "Structure integrity lost (joints broke)"

        success = (in_hopper_count >= self.MIN_PARTICLES_IN_HOPPER and not self.structure_broken and not failed)

        if success:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            score = max(0.0, 80.0 * (in_hopper_count / self.MIN_PARTICLES_IN_HOPPER))

        metrics = self._collect_metrics(
            step_count,
            success=success,
            failed=failed,
            failure_reason=failure_reason,
            initial_count=initial_count,
            in_truck_count=in_hopper_count,
            collected_ratio=collected_ratio,
            agent_body=agent_body,
        )
        return True, score, metrics

    def _collect_metrics(self, step_count, success=False, failed=False, failure_reason=None,
                         initial_count=None, in_truck_count=None, collected_ratio=None,
                         agent_body=None):
        if initial_count is None:
            initial_count = self.environment.get_initial_particle_count()
        if in_truck_count is None:
            in_truck_count = self.environment.get_particles_in_hopper_count()
        if collected_ratio is None and initial_count > 0:
            collected_ratio = in_truck_count / initial_count
        elif collected_ratio is None:
            collected_ratio = 0.0

        metrics = {
            "step_count": step_count,
            "max_steps": self.MAX_STEPS,
            "max_time_seconds": self.MAX_TIME_SECONDS,
            "initial_particle_count": initial_count,
            "particles_in_truck": in_truck_count,
            "collected_ratio": collected_ratio,
            "collected_ratio_percent": collected_ratio * 100.0,
            "min_particles_in_hopper": self.MIN_PARTICLES_IN_HOPPER,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "structure_mass": self.environment.get_structure_mass(),
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "structure_broken": self.structure_broken,
            "joint_count": len(self.environment._joints),
        }
        if agent_body is not None and hasattr(agent_body, 'position'):
            metrics["agent_x"] = agent_body.position.x
            metrics["agent_y"] = agent_body.position.y
            if hasattr(agent_body, 'linearVelocity'):
                metrics["velocity_x"] = agent_body.linearVelocity.x
                metrics["velocity_y"] = agent_body.linearVelocity.y
                metrics["speed"] = (agent_body.linearVelocity.x**2 + agent_body.linearVelocity.y**2) ** 0.5
            if hasattr(agent_body, 'angularVelocity'):
                metrics["angular_velocity"] = agent_body.angularVelocity
            if hasattr(agent_body, 'angle'):
                metrics["bucket_angle_rad"] = agent_body.angle
                metrics["bucket_angle_deg"] = agent_body.angle * 180.0 / math.pi
        # Arm and joint state (process metrics for feedback)
        arm_joint = getattr(self.environment, "agent_arm_joint", None)
        if arm_joint is not None and hasattr(arm_joint, "angle"):
            metrics["arm_joint_angle_rad"] = arm_joint.angle
            metrics["arm_joint_angle_deg"] = arm_joint.angle * 180.0 / math.pi
            # Arm link is bodyB of the arm revolute joint (first moving arm segment)
            if hasattr(arm_joint, "bodyB") and arm_joint.bodyB is not None and arm_joint.bodyB.active:
                arm_body = arm_joint.bodyB
                metrics["arm_x"] = arm_body.position.x
                metrics["arm_y"] = arm_body.position.y
                metrics["arm_angle_rad"] = arm_body.angle
        return metrics

    def _check_design_constraints(self):
        violations = []
        if not self.environment:
            return ["Environment not available"]
        structure_mass = self.environment.get_structure_mass()
        if structure_mass > self.MAX_STRUCTURE_MASS:
            violations.append(f"Structure mass {structure_mass:.2f} kg exceeds maximum {self.MAX_STRUCTURE_MASS} kg")
        
        min_beam = getattr(self.environment, "MIN_BEAM_SIZE", 0.1)
        max_beam = getattr(self.environment, "MAX_BEAM_SIZE", 1.5)
        max_motor = getattr(self.environment, "_max_motor_torque", 100.0)

        for body in self.environment._bodies:
            # 1. Build Zone Check (AABB)
            for fixture in body.fixtures:
                shape = fixture.shape
                if hasattr(shape, 'vertices'):
                    for v in shape.vertices:
                        world_v = body.GetWorldPoint(v)
                        if not (self.BUILD_ZONE_X_MIN - 1e-4 <= world_v.x <= self.BUILD_ZONE_X_MAX + 1e-4 and
                                self.BUILD_ZONE_Y_MIN - 1e-4 <= world_v.y <= self.BUILD_ZONE_Y_MAX + 1e-4):
                            violations.append(
                                f"Component at ({world_v.x:.2f}, {world_v.y:.2f}) is outside build zone "
                                f"x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]"
                            )
                            break
                    else: continue
                    break
                elif hasattr(shape, 'radius'):
                    # For circles/particles (though excavator shouldn't use circles for structure)
                    pass

            # 2. Beam Size Verification
            for fixture in body.fixtures:
                if hasattr(fixture.shape, 'box'): # Not directly available in Box2D-python easily
                    pass 
                # Alternative: check vertices for box dimensions
                if hasattr(fixture.shape, 'vertices'):
                    vs = fixture.shape.vertices
                    if len(vs) == 4:
                        w = max(v[0] for v in vs) - min(v[0] for v in vs)
                        h = max(v[1] for v in vs) - min(v[1] for v in vs)
                        # Box2D stores half-widths in 'box' but vertices are full extent in local coords
                        # add_beam uses polygonShape(box=(width/2, height/2))
                        # So vertices are at +/- width/2.
                        if w < min_beam - 1e-4 or w > max_beam + 1e-4 or h < min_beam - 1e-4 or h > max_beam + 1e-4:
                            # Only report if it's a significant deviation (accounting for scoop thickness etc.)
                            if not (hasattr(self.environment, "_scoop_bodies") and body in self.environment._scoop_bodies):
                                violations.append(f"Beam dimensions {w:.2f}x{h:.2f} m are outside required range [{min_beam}, {max_beam}]")

        # 3. Motor Torque Verification
        for joint in getattr(self.environment, "_revolute_joints", []):
            if joint.maxMotorTorque > max_motor + 1e-4:
                violations.append(f"Motor torque {joint.maxMotorTorque:.1f} N·m exceeds maximum {max_motor:.1f} N·m")

        # Base must be at (-2, 0): at least one body (base) at that position
        has_base_at_required = False
        for body in self.environment._bodies:
            if abs(body.position.x - self.BASE_X) < 0.5 and abs(body.position.y - self.BASE_Y) <= 0.5:
                has_base_at_required = True
                break
        if not has_base_at_required:
            violations.append(f"Base must be fixed at x={self.BASE_X}, y={self.BASE_Y}")
        # At least 2 DOF (revolute joints)
        revolute_count = len(getattr(self.environment, '_revolute_joints', []))
        if revolute_count < 2:
            violations.append(f"Mechanism must have at least 2 degrees of freedom (Arm + Bucket); found {revolute_count} revolute joint(s)")
        return list(set(violations)) # Deduplicate

    def get_task_description(self):
        return {
            "task": "F-03: The Excavator",
            "description": f"Dig sand from pit and transport into hopper; at least {self.MIN_PARTICLES_IN_HOPPER} particles in hopper within {self.MAX_TIME_SECONDS:.0f} s; base at (-2,0), 2 DOF (Arm + Bucket)",
            "terrain": self.terrain_bounds,
            "success_criteria": {
                "primary": f"Deposit at least {self.MIN_PARTICLES_IN_HOPPER} sand particles into the Hopper",
                "secondary": f"Complete within {self.MAX_TIME_SECONDS:.0f} seconds; structure intact",
            },
            "evaluation": {"score_range": "0-100", "success_score": 100, "failure_score": 0},
        }
