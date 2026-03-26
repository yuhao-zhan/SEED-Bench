import re

def update_task_description_for_visible_changes(description, target_mass, base_mass):
    # Fixed regex to match "60 kg" or "60 kg (originally 20 kg in the source environment)"
    # The original description has "A 20 kg block"
    # Try capturing the "20 kg" part properly.
    # Pattern structure: "A 20 kg (originally X kg) block"
    mass_pattern = r"(- \*\*Target Object\*\*: A )(\d+\.?\d*)( kg)( \(originally [\d.]+ kg in the source environment\))?( block)"
    # New version should be "A 60 kg (originally 20 kg in the source environment) block"
    
    # Wait, the current description in prompt is:
    # "- **Target Object**: A 20 kg block..."
    # The groups in mass_pattern:
    # 1: "- **Target Object**: A "
    # 2: "20"
    # 3: " kg"
    # 4: "" (optional)
    # 5: " block"
    
    new_desc = re.sub(
        mass_pattern,
        f"\g<1>{target_mass:.0f}\g<3> (originally {base_mass:.0f} kg in the source environment)\g<5>",
        description,
    )
    return new_desc

desc = """- **Target Object**: A 20 kg block (0.6 m × 0.4 m, width × height), friction coefficient 0.6, resting at x=4.0m, y=1.8m."""
print(update_task_description_for_visible_changes(desc, 60.0, 20.0))
