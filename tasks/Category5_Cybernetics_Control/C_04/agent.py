import math

ACTIVATION_X_MAX = 10.0

ACTIVATION_X_MIN = 5.0

AGENT_MASS = 5.0

BACKWARD_FX_THRESHOLD = -34.0

BACKWARD_SPEED_MAX = 100.0

EXIT_X_MIN = 15.0

HOLD_STEPS = 5

ONEWAY_FORCE_RIGHT = 50.0

ONEWAY_X = 10.2

TIME_STEP = 1.0 / 60.0

def _control_cfg(sandbox):
    return {
        "act_lo": float(getattr(sandbox, "_activation_x_min", ACTIVATION_X_MIN)),
        "act_hi": float(getattr(sandbox, "_activation_x_max", ACTIVATION_X_MAX)),
        "bfx": float(getattr(sandbox, "_backward_fx_threshold", BACKWARD_FX_THRESHOLD)),
        "bspd": float(getattr(sandbox, "_backward_speed_max", BACKWARD_SPEED_MAX)),
        "hold": int(getattr(sandbox, "_backward_steps_required", HOLD_STEPS)),
        "ow_x": float(getattr(sandbox, "_oneway_x", ONEWAY_X)),
        "ow_f": float(getattr(sandbox, "_oneway_force_right", ONEWAY_FORCE_RIGHT)),
    }

class Memory:
    def __init__(self):
        self.data = {}
    def clear(self):
        self.data = {}

MEM = Memory()

def _weight_comp(sandbox):
    try:
        gy = float(sandbox.world.gravity[1])
    except (AttributeError, TypeError, IndexError):
        gy = -9.8
    return float(AGENT_MASS) * abs(gy)

def _exit_x_min(_sandbox):
    return float(EXIT_X_MIN)

def build_agent(sandbox):
    return sandbox.get_agent_body()

def agent_action(sandbox, agent_body, step_count):
    if not hasattr(agent_body, "_controller_state"):
        agent_body._controller_state = {
            "phase": "APPROACH",
            "t": 0,
            "lx": None,
            "ly": None,
            "vx": 0.0,
            "vy": 0.0,
        }
    state = agent_body._controller_state
    cfg = _control_cfg(sandbox)
    pd = sandbox.get_agent_position()
    dt = TIME_STEP
    if state["lx"] is not None:
        state["vx"] = (pd[0] - state["lx"]) / dt
        state["vy"] = (pd[1] - state["ly"]) / dt
    state["lx"], state["ly"] = pd[0], pd[1]
    vxd, vyd = state["vx"], state["vy"]
    x, y = pd[0], pd[1]
    ty, w_comp = 1.5, _weight_comp(sandbox)
    if state["phase"] == "APPROACH":
        fx = 15.0 if x < 5.0 else 10.0 * (7.0 - x) - 5.0 * vxd
        fy = 50.0 * (ty - y) - 20.0 * vyd + w_comp
        if cfg["act_lo"] <= x <= cfg["act_hi"] and abs(vxd) < 0.5:
            state["phase"] = "UNLOCK"
            state["t"] = 0
    elif state["phase"] == "UNLOCK":
        vx_p, vy_p = sandbox.get_agent_velocity()
        spd = math.hypot(vx_p, vy_p)
        fx_cmd = cfg["bfx"] - 1.0
        fy_cmd = 50.0 * (ty - y) - 20.0 * vyd + w_comp
        if spd >= cfg["bspd"] * 0.99:
            horiz = -1.5 * vx_p
            if horiz > 0:
                horiz = 0
            fx_cmd += horiz
            fy_cmd -= 1.5 * vy_p
        fx, fy = fx_cmd, fy_cmd
        state["t"] += 1
        if state["t"] > 60:
            state["phase"] = "ESCAPE"
    elif state["phase"] == "ESCAPE":
        fx, fy = 15.0, 50.0 * (ty - y) - 20.0 * vyd + w_comp
        if x > _exit_x_min(sandbox) + 2.5:
            state["phase"] = "HOLD"
    elif state["phase"] == "HOLD":
        fx, fy = 0.0, w_comp
    sandbox.apply_agent_force(fx, fy)

def build_agent_stage_1(sandbox):
    MEM.clear()
    return sandbox.get_agent_body()

def agent_action_stage_1(sandbox, agent_body, step_count):
    cfg = _control_cfg(sandbox)
    p, v = sandbox.get_agent_position(), sandbox.get_agent_velocity()
    w_comp = _weight_comp(sandbox)
    ty = 1.5
    if "phase1" not in MEM.data:
        MEM.data["phase1"] = "APPROACH"
        MEM.data["t1"] = step_count
    phase = MEM.data["phase1"]
    def creep_fx(f, lo=-0.8, hi=1.35):
        return max(lo, min(hi, f))
    def clamp_y_force(fy):
        return max(28, min(62, fy))
    speed = (v[0] ** 2 + v[1] ** 2) ** 0.5
    if phase != "UNLOCK" and speed > 0.004:
        brake_fx = creep_fx(-2.5 * v[0] - 0.3 * (1.0 if v[0] > 0 else -1.0))
        if phase == "ESCAPE" and p[0] > cfg["ow_x"]:
            fx = -cfg["ow_f"] + brake_fx
        else:
            fx = brake_fx
        fy = clamp_y_force(w_comp - 2.5 * v[1] - 0.3 * (1.0 if v[1] > 0 else -1.0))
        sandbox.apply_agent_force(fx, fy)
        return
    if phase == "APPROACH":
        fx = creep_fx(1.0 * (6.5 - p[0]) - 4.0 * v[0])
        fy = clamp_y_force(32.0 * (ty - p[1]) - 18.0 * v[1] + w_comp)
        if cfg["act_lo"] <= p[0] <= cfg["act_hi"] and abs(v[0]) < 0.06 and 1.1 <= p[1] <= 1.7:
            MEM.data["phase1"] = "UNLOCK"
            MEM.data["t1"] = step_count
    elif phase == "UNLOCK":
        steps_in_unlock = step_count - MEM.data["t1"]
        fx = (cfg["bfx"] - 1.0) if steps_in_unlock < 35 else 0.0
        fy = clamp_y_force(32.0 * (ty - p[1]) - 18.0 * v[1] + w_comp)
        spd = (v[0] ** 2 + v[1] ** 2) ** 0.5
        if steps_in_unlock < 35 and spd >= cfg["bspd"] * 0.99:
            horiz = -1.5 * v[0]
            if horiz > 0:
                horiz = 0
            fx += horiz
            fy = clamp_y_force(fy - 1.5 * v[1])
        if steps_in_unlock >= 120:
            MEM.data["phase1"] = "ESCAPE"
    elif phase == "ESCAPE":
        raw_fx = 0.4 * (17.0 - p[0]) - 2.0 * v[0]
        if p[0] > cfg["ow_x"]:
            if speed > 0.005:
                fx = -cfg["ow_f"] + creep_fx(-2.5 * v[0] - 0.5)
            else:
                creep = max(-0.8, min(0.06, raw_fx))
                fx = -cfg["ow_f"] + creep
        elif p[0] > 5.0:
            if p[0] > 9.0 and speed > 0.01:
                fx = max(-3.0, -2.5 * v[0] - 1.0)
            elif speed > 0.005:
                fx = creep_fx(-2.5 * v[0] - 0.4)
            else:
                cap = 0.02 if p[0] <= cfg["ow_x"] else 0.06
                fx = max(-0.8, min(cap, raw_fx))
        elif p[0] > 3.0:
            if speed > 0.01:
                fx = creep_fx(-2.5 * v[0] - 0.5)
            else:
                cap = 0.5 - (0.5 - 0.06) * (p[0] - 3.0)
                fx = creep_fx(raw_fx, lo=-0.8, hi=cap)
        else:
            fx = creep_fx(1.3 * (17.0 - p[0]) - 4.0 * v[0])
        fy = clamp_y_force(32.0 * (ty - p[1]) - 18.0 * v[1] + w_comp)
        if p[0] > 17.0:
            MEM.data["phase1"] = "HOLD"
    else:
        fx = -cfg["ow_f"] if p[0] > cfg["ow_x"] else 0.0
        fy = w_comp
    sandbox.apply_agent_force(fx, fy)

def build_agent_stage_2(sandbox):
    MEM.clear()
    return sandbox.get_agent_body()

def agent_action_stage_2(sandbox, agent_body, step_count):
    px, py = sandbox.get_agent_position()
    vx, vy = sandbox.get_agent_velocity()
    fy = 60.0 * (2.2 - py) - 30.0 * vy + _weight_comp(sandbox)
    if px < 5.0:
        fx = 20.0
    elif px < 10.0:
        if "u2" not in MEM.data:
            fx = -60.0
            if "s2" not in MEM.data:
                MEM.data["s2"] = 0
            MEM.data["s2"] += 1
            if MEM.data["s2"] > 80:
                MEM.data["u2"] = True
        else:
            fx = 40.0
    else:
        fx = 40.0 if px < 18.0 else -10.0 * vx
    sandbox.apply_agent_force(fx, fy)

def build_agent_stage_3(sandbox):
    MEM.clear()
    return sandbox.get_agent_body()

def agent_action_stage_3(sandbox, agent_body, step_count):
    p, v = sandbox.get_agent_position(), sandbox.get_agent_velocity()
    w_comp = _weight_comp(sandbox)
    speed = (v[0] ** 2 + v[1] ** 2) ** 0.5
    if speed > 16.0:
        fx = -3.0 * v[0] - 80.0 * (1.0 if v[0] > 0 else -1.0)
        fy = w_comp - 3.0 * v[1] - 80.0 * (1.0 if v[1] > 0 else -1.0)
        mag = (fx**2 + fy**2) ** 0.5
        if mag > 400.0:
            fx, fy = fx * 400.0 / mag, fy * 400.0 / mag
        sandbox.apply_agent_force(fx, fy)
        return
    if p[0] < 5.5:
        ty = 2.0
    elif p[0] < 10.0:
        ty = 0.75
    else:
        ty = 1.2
    if p[0] < 5.0:
        fx = 350.0
    elif p[0] < 10.0:
        if "u3" not in MEM.data:
            fx = -200.0
            if "s3" not in MEM.data:
                MEM.data["s3"] = 0
            MEM.data["s3"] += 1
            if MEM.data["s3"] > 120:
                MEM.data["u3"] = True
        else:
            fx = min(900.0, 400.0 + 200.0 * (1.0 - speed / 18.0))
    else:
        fx = min(900.0, 400.0 + 200.0 * (1.0 - speed / 18.0))
    fy = 500.0 * (ty - p[1]) - 120.0 * v[1] + w_comp
    mag = (fx**2 + fy**2) ** 0.5
    if mag > 550.0:
        fx, fy = fx * 550.0 / mag, fy * 550.0 / mag
    sandbox.apply_agent_force(fx, fy)

def build_agent_stage_4(sandbox):
    MEM.clear()
    return sandbox.get_agent_body()

def agent_action_stage_4(sandbox, agent_body, step_count):
    cfg = _control_cfg(sandbox)
    p, v = sandbox.get_agent_position(), sandbox.get_agent_velocity()
    w_comp = _weight_comp(sandbox)
    ty = 1.5
    m_y = float(getattr(sandbox, "_magnetic_floor_y_max", -999.0))
    m_f = float(getattr(sandbox, "_magnetic_floor_force", 0.0))
    y_phys = float(agent_body.position.y) if agent_body is not None else p[1]
    mag_comp = (-m_f) if (m_y > -500.0 and y_phys < m_y) else 0.0
    fy = 500.0 * (ty - p[1]) - 120.0 * v[1] + w_comp + mag_comp
    if "u4" not in MEM.data:
        MEM.data["u4"] = False
        MEM.data["steps4"] = 0
    if not MEM.data["u4"]:
        fx_cmd = -60.0
        speed = (v[0] ** 2 + v[1] ** 2) ** 0.5
        need = cfg["hold"]
        if (
            cfg["act_lo"] <= p[0] <= cfg["act_hi"]
            and fx_cmd < cfg["bfx"]
            and speed < cfg["bspd"]
        ):
            MEM.data["steps4"] += 1
        else:
            MEM.data["steps4"] = 0
        if MEM.data["steps4"] >= need:
            MEM.data["u4"] = True
        if p[0] > 11.0:
            fx_cmd = 60.0
    else:
        if p[0] < 17.5:
            fx_cmd = -100.0
        else:
            fx_cmd = 40.0 * v[0]
    mag = (fx_cmd**2 + fy**2) ** 0.5
    limit = 950.0
    if mag > limit:
        fx_cmd, fy = fx_cmd * limit / mag, fy * limit / mag
    sandbox.apply_agent_force(fx_cmd, fy)
