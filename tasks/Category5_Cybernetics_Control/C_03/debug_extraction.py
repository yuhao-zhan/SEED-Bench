import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.evaluate_cross_mutated import get_reference_solution

try:
    code = get_reference_solution("Category5_Cybernetics_Control/C_03", "Initial")
    print("--- Extracted Code ---")
    print(code)
    print("----------------------")
except Exception as e:
    print(f"Error: {e}")
