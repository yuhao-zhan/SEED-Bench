import math

def simulate(T, M=10.0, m=1.0, l=1.0, L=2.0, g=10.0, dt=1/60.0, steps=1000):
    I = (1/3) * m * L**2
    theta = math.pi
    omega = 0.0
    x = 10.0
    v = 0.0
    max_height = -1e9
    steps_to_top = 1000000
    
    for s in range(steps):
        t = s * dt
        # v(0) = 0 version
        x_target = 10.0 - 5.0 * math.cos(2 * math.pi * t / T)
        v_target = 5.0 * (2 * math.pi / T) * math.sin(2 * math.pi * t / T)
        
        kp = 1000.0
        kd = 200.0
        force = kp * (x_target - x) + kd * (v_target - v)
        force = max(-450.0, min(450.0, force))
        
        sin_th = math.sin(theta)
        cos_th = math.cos(theta)
        numerator = force + (m**2 * l**2 * g / I) * sin_th * cos_th + m * l * omega**2 * sin_th
        denominator = M + m - (m**2 * l**2 / I) * cos_th**2
        x_ddot = numerator / denominator
        theta_ddot = -(m * g * l * sin_th + m * l * x_ddot * cos_th) / I
        
        v += x_ddot * dt
        x += v * dt
        omega += theta_ddot * dt
        theta += omega * dt
        
        height = -math.cos(theta)
        if height > max_height:
            max_height = height
        if abs(math.atan2(math.sin(theta), math.cos(theta))) < 0.1:
            if s < steps_to_top:
                steps_to_top = s
    return max_height, steps_to_top

if __name__ == "__main__":
    best_T = 0
    min_steps = 1000000
    for i in range(150, 401):
        T = i / 100.0
        h, s = simulate(T)
        if h > 0.99 and s < min_steps:
            min_steps = s
            best_T = T
    print(f"Best T: {best_T}, Steps: {min_steps}")
