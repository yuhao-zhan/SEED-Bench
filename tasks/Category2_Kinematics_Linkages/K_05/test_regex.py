import re
from stages import update_task_description_for_visible_changes

desc = 'Design a scissor lift mechanism that can lift objects vertically using motor rotation or linear forces.\n\n## Task Environment\n- **Ground**: A flat horizontal surface at y=1.0m (friction coefficient 0.8).\n- **Target Object**: A 20 kg block (0.6 m × 0.4 m, width × height), friction coefficient 0.6, resting at x=4.0m, y=1.8m.\n- **Target Height**: Lift the object so its center reaches at least y=9.0m.\n- **Build Zone**: x=[0, 8], y=[1, 12]. All structure components must be placed within this zone.\n- **Ceiling**: None (no vertical obstacle).\n\n## Constraints (must satisfy)\n- **Vertical Lift**: Object center reaches y >= 9.0m.\n- **Sustain**: Object held at target height for at least 3.0 seconds (vertical velocity must remain >= -0.4 m/s; sliding down does not count as held).\n- **Mass Budget**: Total structure mass must be less than 60 kg.\n- **Build Zone**: All components must stay within x=[0, 8], y=[1, 12].\n- **Beam Dimensions**: 0.05 <= width, height <= 4.0 meters.\n- **Joint Angle Limits**: Pivot joint angle limits (when used) are clamped to [-π, π] radians.\n- **Slider Translation**: Prismatic (slider) joints have default translation range ±10 m along the axis if not specified.\n- **Motor limits**: Default maximum torque for pivot (revolute) motors is 100 N·m and default maximum force for slider (prismatic) motors is 100 N if not specified when calling `set_motor` or `set_slider_motor`.\n- **Joint reaction limit**: Structural joints do not break under reaction force in the base environment.\n- **Lifting threshold**: For failure detection, the object is considered "lifted" only when its center rises at least 0.5 m above its initial height (y=1.8 m).\n\n## Instructions\n1. **Design**: Create a scissor lift or telescoping mechanism.\n2. **Control**: Use `set_motor` on pivot joints or `set_slider_motor` on prismatic joints to drive the lift.\n'

target_terrain = {'target_object_y': 10.0, 'max_structure_mass': 50.0, 'object': {'mass': 40.0, 'friction': 0.2}}
base_terrain = {'target_object_y': 9.0, 'max_structure_mass': 60.0, 'object': {'mass': 20.0, 'friction': 0.6}}

new_desc = update_task_description_for_visible_changes(desc, target_terrain, base_terrain)
print(new_desc)

assert "`set_motor`" in new_desc
assert "`set_slider_motor`" in new_desc
