"""
C-03: The Seeker reference agent (Two Rendezvous then Track)
- Body-fixed: thrust is along current heading only; command (fx, fy) toward target so heading aligns and thrust is effective.
- Phase 0 (activation): go to activation zone center and hold for 120+ consecutive steps.
- Phase 1: achieve first rendezvous in window 1 [3500, 5000].
- Phase 2: achieve second rendezvous in window 2 [6000, 7500].
- Phase 3: track until end. Avoid cooldown; match velocity before closing; fuel-efficient.
"""
import math

TIME_STEP = 1.0 / 60.0
MAX_THRUST = 200.0
THRUST_CAP_NO_COOLDOWN = 100.0
SEEKER_MASS = 20.0
HISTORY_LEN = 25
DELAY_ESTIMATE_STEPS = 4
BLIND_ZONE_X_MIN = 12.0
BLIND_ZONE_X_MAX = 15.0
JUMP_THRESHOLD_SQ = 4.0
REPEL_GAIN = 45.0
REPEL_RANGE = 1.4

ACTIVATION_ZONE_X_MIN = 13.0
ACTIVATION_ZONE_X_MAX = 17.0
ACTIVATION_ZONE_CENTER = 15.0
ACTIVATION_HOLD_STEPS = 130
ACTIVATION_PHASE_END = 800

SLOTS_PHASE1 = [(3720, 3780), (4220, 4280), (4720, 4780)]
SLOTS_PHASE2 = [(6220, 6280), (6720, 6780), (7220, 7280)]
RENDEZVOUS_WINDOW1_LO = 3720
RENDEZVOUS_WINDOW1_HI = 4780
RENDEZVOUS_WINDOW2_LO = 6220
RENDEZVOUS_WINDOW2_HI = 7280
RENDEZVOUS_ZONE_X_MIN = 10.0
RENDEZVOUS_ZONE_X_MAX = 20.0
HEADING_ALIGN_TOL_RAD = 0.55
EVASIVE_SAFE_DIST = 4.5
SPEED_CAP_FOR_SENSING = 1.92
MAX_STEPS = 10000

_target_pos_history = []
_last_pred_x = None
_last_pred_y = None
_smooth_tx = None
_smooth_ty = None
SMOOTH_ALPHA = 0.12


def _point_to_rect_dist(px, py, cx, cy, hw, hh):
    dx = max(0, abs(px - cx) - hw)
    dy = max(0, abs(py - cy) - hh)
    return math.sqrt(dx * dx + dy * dy)


def _repel_dir(sx, sy, tx, ty, cx, cy, hw, hh):
    dist = _point_to_rect_dist(sx, sy, cx, cy, hw, hh)
    if dist >= REPEL_RANGE or dist < 0.01:
        return (0.0, 0.0)
    nx = max(cx - hw, min(cx + hw, sx))
    ny = max(cy - hh, min(cy + hh, sy))
    dx = sx - nx
    dy = sy - ny
    d = math.sqrt(dx * dx + dy * dy)
    if d < 0.01:
        dx, dy = sx - cx, sy - cy
        d = math.sqrt(dx * dx + dy * dy)
        if d < 0.01:
            return (0.0, 0.0)
    return (dx / d, dy / d)


def build_agent(sandbox):
    return sandbox.get_seeker_body()


def _estimate_target_velocity(history, dt):
    if len(history) < 2:
        return (0.0, 0.0)
    (s0, x0, y0) = history[0]
    (s1, x1, y1) = history[-1]
    steps = s1 - s0
    if steps <= 0:
        return (0.0, 0.0)
    t_elapsed = steps * dt
    if t_elapsed < 0.05:
        if len(history) >= 3:
            (s0, x0, y0) = history[-3]
            (s1, x1, y1) = history[-1]
            steps = s1 - s0
            t_elapsed = steps * dt
        if t_elapsed < 0.05:
            return (0.0, 0.0)
    vx = (x1 - x0) / t_elapsed
    vy = (y1 - y0) / t_elapsed
    return (vx, vy)


def agent_action(sandbox, agent_body, step_count):
    global _target_pos_history, _last_pred_x, _last_pred_y, _smooth_tx, _smooth_ty

    sx, sy = sandbox.get_seeker_position()
    vx, vy = sandbox.get_seeker_velocity()
    seeker_speed = math.sqrt(vx * vx + vy * vy)
    tx_delayed, ty_delayed = sandbox.get_target_position()
    obstacles = sandbox.get_terrain_obstacles()
    wx, wy = sandbox.get_local_wind()
    budget = sandbox.get_remaining_impulse_budget()
    x_lo, x_hi = sandbox.get_corridor_bounds()
    corridor_width = x_hi - x_lo
    in_central = RENDEZVOUS_ZONE_X_MIN <= sx <= RENDEZVOUS_ZONE_X_MAX
    in_any_slot1 = any(lo <= step_count <= hi for (lo, hi) in SLOTS_PHASE1)
    in_any_slot2 = any(lo <= step_count <= hi for (lo, hi) in SLOTS_PHASE2)
    heading = sandbox.get_seeker_heading()

    _target_pos_history.append((step_count, tx_delayed, ty_delayed))
    if len(_target_pos_history) > HISTORY_LEN:
        _target_pos_history.pop(0)

    tvx, tvy = _estimate_target_velocity(_target_pos_history, TIME_STEP)
    delay_time = DELAY_ESTIMATE_STEPS * TIME_STEP
    in_blind = BLIND_ZONE_X_MIN <= sx <= BLIND_ZONE_X_MAX

    if in_blind:
        if _last_pred_x is not None and _last_pred_y is not None:
            _last_pred_x += tvx * TIME_STEP
            _last_pred_y += tvy * TIME_STEP
        else:
            _last_pred_x = tx_delayed + tvx * delay_time
            _last_pred_y = ty_delayed + tvy * delay_time
        tx, ty = _last_pred_x, _last_pred_y

        if step_count > RENDEZVOUS_WINDOW2_HI:
            tx = max(tx, sx + 1.5, BLIND_ZONE_X_MAX + 0.5)
            if _smooth_tx is not None and _smooth_tx < BLIND_ZONE_X_MAX:
                _smooth_tx = BLIND_ZONE_X_MAX + 0.3
                _smooth_ty = ty
    else:
        pred_x = tx_delayed + tvx * delay_time
        pred_y = ty_delayed + tvy * delay_time
        if _last_pred_x is not None and _last_pred_y is not None:
            dev_sq = (tx_delayed - _last_pred_x) ** 2 + (ty_delayed - _last_pred_y) ** 2
            if dev_sq > JUMP_THRESHOLD_SQ:
                pred_x = tx_delayed + tvx * delay_time
                pred_y = ty_delayed + tvy * delay_time
        _last_pred_x, _last_pred_y = pred_x, pred_y
        tx, ty = pred_x, pred_y

    dist_to_target = math.sqrt((tx - sx) ** 2 + (ty - sy) ** 2)
    rel_vx = vx - tvx
    rel_vy = vy - tvy
    rel_speed = math.sqrt(rel_vx * rel_vx + rel_vy * rel_vy)
    zone_center_x = (RENDEZVOUS_ZONE_X_MIN + RENDEZVOUS_ZONE_X_MAX) * 0.5


    center_corridor = (x_lo + x_hi) * 0.5
    if sx < center_corridor - 0.5 and step_count < 2000:
        tx_blend_corr = center_corridor
    else:
        tx_blend_corr = None

    in_activation_zone = ACTIVATION_ZONE_X_MIN <= sx <= ACTIVATION_ZONE_X_MAX



    target_speed = math.sqrt(tvx * tvx + tvy * tvy)
    if target_speed >= 0.15:
        target_vel_dir = math.atan2(tvy, tvx)
    else:
        target_vel_dir = math.atan2(ty - sy, tx - sx)
    align_ax = sx + 4.0 * math.cos(target_vel_dir)
    align_ay = sy + 4.0 * math.sin(target_vel_dir)

    if step_count < ACTIVATION_PHASE_END:
        if not in_activation_zone:
            tx_blend = ACTIVATION_ZONE_CENTER
            ty_blend = sy
        else:

            tx_blend = 0.3 * sx + 0.7 * ACTIVATION_ZONE_CENTER
            ty_blend = sy
        if tx_blend_corr is not None and not in_activation_zone:
            tx_blend = tx_blend * 0.5 + tx_blend_corr * 0.5
    elif step_count < RENDEZVOUS_WINDOW1_LO:

        if dist_to_target > EVASIVE_SAFE_DIST or not in_central:
            tx_blend = tx * 0.65 + zone_center_x * 0.35
            ty_blend = ty
        else:
            tx_blend = tx * 0.6 + sx * 0.2 + (tx - sx) * 0.2
            ty_blend = ty * 0.6 + sy * 0.2 + (ty - sy) * 0.2
        if tx_blend_corr is not None:
            tx_blend = tx_blend * 0.5 + tx_blend_corr * 0.5
    elif in_any_slot1:

        tx_blend = 0.55 * align_ax + 0.45 * tx
        ty_blend = 0.55 * align_ay + 0.45 * ty
        if tx_blend_corr is not None:
            tx_blend = tx_blend * 0.7 + tx_blend_corr * 0.3
    elif step_count < RENDEZVOUS_WINDOW2_LO:

        if dist_to_target > 4.0 or not in_central:
            tx_blend = tx * 0.75 + zone_center_x * 0.25
            ty_blend = ty
        else:
            tx_blend = tx * 0.7 + sx * 0.15 + (tx - sx) * 0.15
            ty_blend = ty * 0.7 + sy * 0.15 + (ty - sy) * 0.15
        if tx_blend_corr is not None:
            tx_blend = tx_blend * 0.7 + tx_blend_corr * 0.3
    elif in_any_slot2:

        tx_blend = 0.55 * align_ax + 0.45 * tx
        ty_blend = 0.55 * align_ay + 0.45 * ty
        if tx_blend_corr is not None:
            tx_blend = tx_blend * 0.7 + tx_blend_corr * 0.3
    else:
        tx_blend, ty_blend = tx, ty
        if tx_blend_corr is not None:
            tx_blend = tx_blend * 0.7 + tx_blend_corr * 0.3

    if _smooth_tx is None:
        _smooth_tx, _smooth_ty = tx_blend, ty_blend
    _smooth_tx = _smooth_tx + SMOOTH_ALPHA * (tx_blend - _smooth_tx)
    _smooth_ty = _smooth_ty + SMOOTH_ALPHA * (ty_blend - _smooth_ty)
    tx_ctl, ty_ctl = _smooth_tx, _smooth_ty


    margin = 1.3
    if sx < x_lo + margin:
        ax_corr = 25.0 * (x_lo + margin - sx)
    elif sx > x_hi - margin:
        ax_corr = -25.0 * (sx - (x_hi - margin))
    else:
        ax_corr = 0.0
    pinch_mode = corridor_width < 12.0
    if pinch_mode:
        center_corridor = (x_lo + x_hi) * 0.5
        ax_corr += 12.0 * (center_corridor - sx)



    if in_any_slot1 or in_any_slot2:
        if dist_to_target > 2.5:
            kp = 95.0
            kd = 14.0
        elif dist_to_target < EVASIVE_SAFE_DIST and dist_to_target > 0.1:
            kp = 38.0
            kd = 19.0
        else:
            kp = 72.0
            kd = 15.0
    elif dist_to_target > 5.5:
        kp = 82.0
        kd = 16.0
    elif dist_to_target < EVASIVE_SAFE_DIST and dist_to_target > 0.1:
        kp = 35.0
        kd = 18.0
    else:
        kp = 70.0
        kd = 14.0

    ax = kp * (tx_ctl - sx) - kd * (vx - tvx) + ax_corr
    ay = kp * (ty_ctl - sy) - kd * (vy - tvy)

    for (cx, cy, hw, hh) in obstacles:
        rx, ry = _repel_dir(sx, sy, tx, ty, cx, cy, hw, hh)
        if rx != 0 or ry != 0:
            dist = _point_to_rect_dist(sx, sy, cx, cy, hw, hh)
            strength = REPEL_GAIN * max(0, 1.0 / (dist + 0.2) - 1.0 / (REPEL_RANGE + 0.2))
            ax += rx * strength
            ay += ry * strength

    ax -= wx
    ay -= wy

    fx = SEEKER_MASS * ax
    fy = SEEKER_MASS * ay
    mag = math.sqrt(fx * fx + fy * fy)


    steps_left = max(1, MAX_STEPS - step_count)
    budget_per_step = budget / (steps_left * TIME_STEP)
    thrust_cap = THRUST_CAP_NO_COOLDOWN
    if step_count < ACTIVATION_PHASE_END:
        thrust_cap = 110.0
    elif (in_any_slot1 or in_any_slot2) and dist_to_target > 1.5:
        thrust_cap = 120.0
    elif (step_count > RENDEZVOUS_WINDOW1_HI or step_count > RENDEZVOUS_WINDOW2_HI) and dist_to_target > 4.0:
        thrust_cap = min(115.0, THRUST_CAP_NO_COOLDOWN + 15.0)
    max_mag_step = min(thrust_cap, max(50.0, budget_per_step * 0.96))
    if pinch_mode:
        max_mag_step = min(max_mag_step, 60.0)


    if not in_blind and seeker_speed > SPEED_CAP_FOR_SENSING and (in_any_slot1 or in_any_slot2):
        max_mag_step = min(max_mag_step, 50.0)

    if mag > 1e-9:
        scale = min(max_mag_step, mag) / mag
        fx *= scale
        fy *= scale

    sandbox.apply_seeker_force(fx, fy)
