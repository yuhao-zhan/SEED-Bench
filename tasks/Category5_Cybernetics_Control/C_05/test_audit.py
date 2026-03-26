import re
from tasks.Category5_Cybernetics_Control.C_05.stages import UNIFORM_SUFFIX

def test_uniform_suffix():
    # Check if suffix leaks specific stage mutations
    # Stage 1: speed_cap_inside, recent_a_for_b, recent_b_for_c, c_high_history
    # Stage 2: trigger_stay_steps, speed_cap_inside, repulsion_mag, recent_a_for_b, recent_b_for_c, c_high_history
    # Stage 3: speed_cap_inside, repulsion_mag, repulsion_tangential_mag, force_limit_inside, trigger_stay_steps, recent_a_for_b, recent_b_for_c, c_high_history, ramp_friction
    # Stage 4: speed_cap_inside, repulsion_mag, repulsion_tangential_mag, force_limit_inside, trigger_stay_steps, barrier_delay_steps, recent_a_for_b, recent_b_for_c, c_high_history, ramp_friction, ground_friction
    
    # Audit Rule: Must not pinpoint exact mutations, specific values, or directions of change.
    leaks = []
    # Any numbers or specific mutation terminology that could be considered "pinpointing"
    if re.search(r'\d+', UNIFORM_SUFFIX):
        leaks.append("Found numbers in UNIFORM_SUFFIX")
    
    # Scan for "increase", "decrease", "higher", "lower" etc.
    forbidden_terms = ["increase", "decrease", "higher", "lower", "faster", "slower", "stronger", "weaker"]
    for term in forbidden_terms:
        if term in UNIFORM_SUFFIX.lower():
            leaks.append(f"Found forbidden term: {term}")
            
    assert not leaks, f"UNIFORM_SUFFIX leaks detected: {leaks}"

if __name__ == "__main__":
    test_uniform_suffix()
    print("UNIFORM_SUFFIX audit passed.")
