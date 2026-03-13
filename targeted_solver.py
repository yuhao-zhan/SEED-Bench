import math

def simulate(vx0, vy0, g, b, dt=1.0/60.0):
    x, y = 5.0, 5.0
    vx, vy = vx0, vy0
    
    slots = [
        (17.0, 13.2, 14.7), # Slot 1
        (19.0, 12.4, 14.2), # Slot 3
        (21.0, 11.3, 13.3), # Slot 2
    ]
    
    passed_slots = [False] * len(slots)
    
    for i in range(3000):
        # Apply damping
        vx *= (1.0 - dt * b)
        vy *= (1.0 - dt * b)
        # Apply gravity
        vy += g * dt
        
        # Update position
        x += vx * dt
        y += vy * dt
        
        # Check slots
        JUMPER_HALF_W, JUMPER_HALF_H = 0.4, 0.3
        SLOT_MARGIN = 0.05
        
        for j, (bx_center, floor_y, ceil_y) in enumerate(slots):
            bx_min, bx_max = bx_center - 0.5, bx_center + 0.5
            in_x_range = x - JUMPER_HALF_W <= bx_max and x + JUMPER_HALF_W >= bx_min
            if in_x_range:
                if y - JUMPER_HALF_H <= floor_y + SLOT_MARGIN or y + JUMPER_HALF_H >= ceil_y - SLOT_MARGIN:
                    return False, j, f"Hit slot {j+1}"
                passed_slots[j] = True
        
        # Check if landed
        if x >= 26.0:
            if y >= 1.0:
                if all(passed_slots):
                    return True, 3, "Success"
                else:
                    return False, sum(passed_slots), f"Missed slots: {passed_slots}"
            else:
                return False, sum(passed_slots), f"Fell into pit"
                
        if y < 0:
            return False, sum(passed_slots), f"Fell into pit"
            
    return False, sum(passed_slots), "Timeout"

# Stage-2: g=-14, b=1.8
for vx in [x * 0.2 for x in range(250, 1000)]:
    for vy in [y * 0.2 for y in range(100, 800)]:
        success, n_slots, msg = simulate(vx, vy, -14, 1.8)
        if success:
            print(f"Stage-2: vx={vx:.2f}, vy={vy:.2f}")
            break
    else: continue
    break
else:
    print("Stage-2 not found")

# Stage-3: g=-20, b=1.2
for vx in [x * 0.2 for x in range(100, 800)]:
    for vy in [y * 0.2 for y in range(100, 800)]:
        success, n_slots, msg = simulate(vx, vy, -20, 1.2)
        if success:
            print(f"Stage-3: vx={vx:.2f}, vy={vy:.2f}")
            break
    else: continue
    break
else:
    print("Stage-3 not found")

# Stage-4: g=-23, b=2.0
for vx in [x * 0.2 for x in range(250, 1200)]:
    for vy in [y * 0.2 for y in range(100, 1000)]:
        success, n_slots, msg = simulate(vx, vy, -23, 2.0)
        if success:
            print(f"Stage-4: vx={vx:.2f}, vy={vy:.2f}")
            break
    else: continue
    break
else:
    print("Stage-4 not found")
