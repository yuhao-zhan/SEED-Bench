import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

def debug_env():
    task_name = "Category5_Cybernetics_Control.C_02"
    task_module = __import__(f"tasks.{task_name}", fromlist=["environment"])
    env = task_module.environment.Sandbox()
    bounds = env.get_terrain_bounds()
    print(f"Barrier X: [{bounds['barrier_x_left']}, {bounds['barrier_x_right']}]")
    print(f"Barrier Y: Top={bounds['barrier_y_top']}, Bottom={bounds['barrier_y_bottom']}")

if __name__ == "__main__":
    debug_env()
