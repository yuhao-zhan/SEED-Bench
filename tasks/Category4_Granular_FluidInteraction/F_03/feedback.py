"""
Task-specific feedback for F-03: The Excavator.
Process-aware, diagnostic feedback — no spoilers, no hallucination, dynamic thresholds.
Adapts to stage mutations (gravity, friction, damping, min_particles_in_hopper, build zone, scoop capacity).
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from evaluator.evaluate() only.
    No suggestions; no metrics that are not present in the metrics dict.
    """
    parts = []

    # Design-constraint failure (evaluator returns minimal dict with constraint_violations)
    constraint_violations = metrics.get("constraint_violations")
    if constraint_violations is not None and isinstance(constraint_violations, list):
        parts.append("### 0. Design Constraint Violations")
        for v in constraint_violations:
            parts.append(f"- {v}")
        # May have no other metrics; return early only if this is the only content
        if not any(
            k in metrics
            for k in (
                "structure_mass",
                "structure_broken",
                "particles_in_truck",
                "collected_ratio_percent",
                "step_count",
            )
        ):
            return parts
        parts.append("")

    # 1. Structural design & constraints (dynamic: max_structure_mass from env/stage)
    struct_keys = ["structure_mass", "max_structure_mass", "joint_count", "structure_broken"]
    if any(k in metrics for k in struct_keys):
        parts.append("### 1. Structural Design & Constraints")
        max_mass = metrics.get("max_structure_mass")
        if "structure_mass" in metrics:
            mass = metrics["structure_mass"]
            if max_mass is not None:
                margin = (max_mass - mass) if max_mass != 0 else 0.0
                parts.append(
                    f"- Total Structure Mass: {mass:.2f} / {max_mass:.2f} kg "
                    f"(margin: {margin:.2f} kg)"
                )
            else:
                parts.append(f"- Total Structure Mass: {mass:.2f} kg")
        if "structure_broken" in metrics:
            parts.append(
                "- Structural Integrity: "
                + ("FAILED (one or more joints broke during simulation)" if metrics["structure_broken"] else "NOMINAL (intact)")
            )
        if "joint_count" in metrics:
            parts.append(f"- Active Joint Count: {metrics['joint_count']}")

    # 2. Task performance & granular transfer (dynamic: min_particles_in_hopper from env/stage)
    perf_keys = ["particles_in_truck", "min_particles_in_hopper", "collected_ratio_percent", "initial_particle_count"]
    if any(k in metrics for k in perf_keys):
        parts.append("\n### 2. Task Performance & Granular Transfer")
        target = metrics.get("min_particles_in_hopper")
        in_hopper = metrics.get("particles_in_truck")
        initial = metrics.get("initial_particle_count")
        if in_hopper is not None:
            if target is not None:
                shortfall = max(0, target - in_hopper)
                parts.append(
                    f"- Particles in Hopper: {in_hopper} (required: ≥ {target})"
                    + (f" — shortfall: {shortfall}" if shortfall > 0 else " — target met")
                )
            else:
                parts.append(f"- Particles in Hopper: {in_hopper}")
        if "collected_ratio_percent" in metrics:
            parts.append(f"- Material Transfer Ratio: {metrics['collected_ratio_percent']:.1f}%")
        if initial is not None and initial > 0 and in_hopper is not None:
            parts.append(f"- Source Pool: {initial} particles initially")

    # 3. Temporal / operational
    if "step_count" in metrics:
        parts.append("\n### 3. Operational Timeline")
        step_count = metrics["step_count"]
        max_steps = metrics.get("max_steps")
        if max_steps is not None:
            margin = max_steps - step_count
            parts.append(f"- Simulation Steps: {step_count} / {max_steps} (margin: {margin} steps)")
        else:
            parts.append(f"- Simulation Steps: {step_count}")

    # 4. Physical process & kinematics (only if present — agent_body / arm state)
    kin_keys = ["velocity_x", "velocity_y", "speed", "bucket_angle_deg", "arm_joint_angle_deg", "agent_x", "agent_y", "arm_x", "arm_y", "angular_velocity"]
    if any(k in metrics for k in kin_keys):
        parts.append("\n### 4. Physical Process & Kinematics (End-State)")
        vx, vy = metrics.get("velocity_x"), metrics.get("velocity_y")
        if vx is not None and vy is not None:
            parts.append(f"- End-Effector Velocity: [{vx:.2f}, {vy:.2f}] m/s")
        if "speed" in metrics and metrics["speed"] is not None:
            parts.append(f"- Absolute Speed: {metrics['speed']:.2f} m/s")
        if "bucket_angle_deg" in metrics or "arm_joint_angle_deg" in metrics:
            bucket = metrics.get("bucket_angle_deg")
            arm = metrics.get("arm_joint_angle_deg")
            if bucket is not None or arm is not None:
                ang_parts = []
                if bucket is not None:
                    ang_parts.append(f"Bucket {bucket:.1f}°")
                if arm is not None:
                    ang_parts.append(f"Arm {arm:.1f}°")
                parts.append("- Actuator Angles: " + ", ".join(ang_parts))
        if "agent_x" in metrics and "agent_y" in metrics:
            parts.append(f"- Bucket Position: ({metrics['agent_x']:.2f}, {metrics['agent_y']:.2f}) m")
        if "arm_x" in metrics and "arm_y" in metrics:
            parts.append(f"- Arm Link Position: ({metrics['arm_x']:.2f}, {metrics['arm_y']:.2f}) m")
        if "angular_velocity" in metrics and metrics["angular_velocity"] is not None:
            parts.append(f"- Angular Velocity: {metrics['angular_velocity']:.2f} rad/s")

    return parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Diagnostic, process-aware suggestions only. No spoilers: diagnose physical/systemic
    cause without prescribing exact design or code. All thresholds from metrics (stage-adaptive).
    """
    suggestions = []
    reason = ((error or "") + " " + (failure_reason or "")).strip().lower()

    # Dynamic thresholds — never hardcode; use evaluator/env values from metrics
    max_mass = metrics.get("max_structure_mass")
    min_particles = metrics.get("min_particles_in_hopper")
    structure_broken = metrics.get("structure_broken", False)
    particles_in_truck = metrics.get("particles_in_truck", 0)
    structure_mass = metrics.get("structure_mass")

    # Design-constraint branch (before run started)
    if "design constraint" in reason or (metrics.get("constraint_violations")):
        if "mass" in reason or (structure_mass is not None and max_mass is not None and structure_mass > max_mass):
            suggestions.append(
                "Diagnostic: Structural mass exceeds the permitted budget for this environment. "
                "The gravitational load capacity or stage limit is being violated; consider the "
                "strength-to-weight ratio of the design."
            )
        if "build zone" in reason or "outside build zone" in reason:
            suggestions.append(
                "Diagnostic: Geometric boundary violation. At least one component lies outside "
                "the permitted construction volume; ensure the full mechanism and its motion envelope "
                "remain within the allowed region."
            )
        if "base" in reason or "fixed" in reason or "anchored" in reason:
            suggestions.append(
                "Diagnostic: Base placement does not satisfy the required fixed anchor position "
                "enforced by the evaluator for this task."
            )
        if "degrees of freedom" in reason or "revolute" in reason or "dof" in reason:
            suggestions.append(
                "Diagnostic: Insufficient kinematic degrees of freedom. The mechanism does not "
                "meet the minimum required articulating joints for the multi-phase dig–lift–dump task."
            )
        return suggestions

    # Post-run failure: root-cause and multi-objective
    if failed:
        # Multi-objective trade-off: good on one axis, fail on another
        target_met = (
            min_particles is not None
            and particles_in_truck is not None
            and particles_in_truck >= min_particles
        )
        if target_met and structure_broken:
            suggestions.append(
                "Diagnostic: Material transfer target was reached or exceeded, but the structure "
                "failed during the process. Load-bearing or dynamic stress at the joints exceeded "
                "their capacity; consider how dead load and motion-induced loads combine."
            )
        elif not target_met and structure_broken:
            suggestions.append(
                "Diagnostic: Structural integrity was lost before the transfer goal was achieved. "
                "Identifying whether joint failure was due to static (self-weight) or dynamic "
                "(motion/impact) loading can guide redesign."
            )

        # Root-cause: structure broke vs insufficient transfer
        if structure_broken:
            suggestions.append(
                "Diagnostic: At least one joint broke during the simulation. Infer whether failure "
                "occurred under sustained load (e.g. lifting) or during a transient event (e.g. "
                "impact or rapid motion); this distinguishes strength vs control issues."
            )
        if "deposited" in reason or "particles" in reason or "hopper" in reason:
            if particles_in_truck == 0:
                suggestions.append(
                    "Diagnostic: No material reached the hopper. The mechanism may not be acquiring "
                    "granular material from the source zone, retaining it during transport, or "
                    "releasing it in the target zone—each phase has different physical requirements."
                )
            else:
                shortfall = (
                    (min_particles - particles_in_truck)
                    if (min_particles is not None and particles_in_truck is not None)
                    else None
                )
                if shortfall is not None and shortfall > 0:
                    suggestions.append(
                        "Diagnostic: Transfer volume is below the required threshold. Consider "
                        "whether the bottleneck is capture efficiency, retention during transport, "
                        "cycle count within the time window, or per-cycle capacity limits."
                    )

    return suggestions
