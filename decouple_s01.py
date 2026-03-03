import re

with open('tasks/Category1_Statics_Equilibrium/S_01/agent.py', 'r') as f:
    content = f.read()

parts = content.split('# --- Mutated Task Solutions ---')
top_part = parts[0]
bottom_part = parts[1]

# Extract _build_generic_bridge
generic_bridge_match = re.search(r'def _build_generic_bridge\(.*?\):.*?(?=def build_agent_stage_1)', bottom_part, re.DOTALL)
generic_bridge_code = generic_bridge_match.group(0)

# Replace it with independent implementations
stages = [
    (1, "num_segments=3"),
    (2, "num_segments=2, num_layers=2"),
    (3, "num_segments=3, deck_density=4.0, support_density=2.0"),
    (4, "num_segments=4, num_layers=3, support_y_offset=3.5, num_verticals=20")
]

new_bottom = "\n# --- Mutated Task Solutions ---\n"

for stage_num, args in stages:
    # create specialized build_agent_stage_X
    # replace args in generic bridge signature
    func_code = generic_bridge_code.replace("def _build_generic_bridge(sandbox, num_segments=2, deck_density=5.0, support_density=3.0, \n                         num_layers=1, support_y_offset=1.5, num_verticals=12):", f"def build_agent_stage_{stage_num}(sandbox):")
    func_code = func_code.replace("def _build_generic_bridge(sandbox, num_segments=2, deck_density=5.0, support_density=3.0, num_layers=1, support_y_offset=1.5, num_verticals=12):", f"def build_agent_stage_{stage_num}(sandbox):")
    
    # We need to properly replace variables using regex
    func_code = re.sub(r'def _build_generic_bridge\(.*?\):', f'def build_agent_stage_{stage_num}(sandbox):', func_code, flags=re.DOTALL)
    
    # Set the variables manually at the top of the function
    var_lines = []
    
    if "num_segments=" in args:
        val = re.search(r'num_segments=([0-9]+)', args).group(1)
        var_lines.append(f"    num_segments = {val}")
    else:
        var_lines.append(f"    num_segments = 2")
        
    if "deck_density=" in args:
        val = re.search(r'deck_density=([0-9.]+)', args).group(1)
        var_lines.append(f"    deck_density = {val}")
    else:
        var_lines.append(f"    deck_density = 5.0")
        
    if "support_density=" in args:
        val = re.search(r'support_density=([0-9.]+)', args).group(1)
        var_lines.append(f"    support_density = {val}")
    else:
        var_lines.append(f"    support_density = 3.0")
        
    if "num_layers=" in args:
        val = re.search(r'num_layers=([0-9]+)', args).group(1)
        var_lines.append(f"    num_layers = {val}")
    else:
        var_lines.append(f"    num_layers = 1")
        
    if "support_y_offset=" in args:
        val = re.search(r'support_y_offset=([0-9.]+)', args).group(1)
        var_lines.append(f"    support_y_offset = {val}")
    else:
        var_lines.append(f"    support_y_offset = 1.5")
        
    if "num_verticals=" in args:
        val = re.search(r'num_verticals=([0-9]+)', args).group(1)
        var_lines.append(f"    num_verticals = {val}")
    else:
        var_lines.append(f"    num_verticals = 12")
        
    var_code = "\n".join(var_lines)
    
    lines = func_code.split('\n')
    
    # find where to insert
    insert_idx = 1
    for i, line in enumerate(lines):
        if 'bounds =' in line:
            insert_idx = i
            break
            
    final_func_code = '\n'.join(lines[:insert_idx]) + '\n' + var_code + '\n' + '\n'.join(lines[insert_idx:])
    
    new_bottom += "\n" + final_func_code
    
    # Add agent action
    if stage_num == 2:
        new_bottom += f"\ndef agent_action_stage_{stage_num}(sandbox, agent_body, step_count):\n    _base_agent_action(sandbox, agent_body, step_count, target_speed=3.0)\n"
    elif stage_num == 4:
        new_bottom += f"\ndef agent_action_stage_{stage_num}(sandbox, agent_body, step_count):\n    _base_agent_action(sandbox, agent_body, step_count, target_speed=2.5)\n"
    else:
        new_bottom += f"\ndef agent_action_stage_{stage_num}(sandbox, agent_body, step_count):\n    _base_agent_action(sandbox, agent_body, step_count)\n"

with open('tasks/Category1_Statics_Equilibrium/S_01/agent.py', 'w') as f:
    f.write(top_part + new_bottom)
