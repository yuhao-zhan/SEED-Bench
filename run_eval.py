import sys
import os

# Ensure the project root is in the path
sys.path.insert(0, os.path.abspath('.'))

from main import run_task

result = run_task(
    "Category4_Granular_FluidInteraction.F_03",
    headless=True,
    max_steps=2400,
    save_gif=False,
)
print(result)
