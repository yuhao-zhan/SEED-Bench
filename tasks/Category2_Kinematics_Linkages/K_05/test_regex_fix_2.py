import re

def update_task_description_for_visible_changes(description, target_mass, base_mass):
    mass_pattern = r"(- \*\*Target Object\*\*: A )(\d+\.?\d*)( kg)( \(originally [\d.]+ kg in the source environment\))?( block(?: \([\d.]+ m × [\d.]+ m, width × height\))?(?:, friction coefficient [\d.]+(?: \(originally [\d.]+ in the source environment\))?)?, resting at x=)"
    
    # Try with original values
    new_desc = re.sub(
        mass_pattern,
        f"\g<1>{target_mass:.0f} kg (originally {base_mass:.0f} kg in the source environment)\g<5>",
        description,
    )
    return new_desc

desc = """- **Target Object**: A 20 kg block (0.6 m × 0.4 m, width × height), friction coefficient 0.6, resting at x=4.0m, y=1.8m."""
print(update_task_description_for_visible_changes(desc, 60.0, 20.0))
