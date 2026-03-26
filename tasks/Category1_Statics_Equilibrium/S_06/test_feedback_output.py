
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from tasks.Category1_Statics_Equilibrium.S_06.feedback import format_task_metrics

def test_feedback():
    # Sample metrics that might come from Stage-1
    metrics = {
        'max_x_position': 0.1,
        'target_overhang': 0.8,
        'stable_duration': 10.0,
        'target_stability_time': 10.0,
        'stability_ok': True,
        'overhang_ok': False,
        'success': False,
        'failed': False,
        'failure_reason': None,
        'step_count': 600,
        'min_y_position': 0.1,
        'max_y_position': 0.3,
        'structure_mass': 0.4,
        'total_kinetic_energy': 0.0,
        'max_velocity': 0.0,
        'block_count': 2,
        'max_block_count_limit': 100,
        'max_total_mass_limit': 20000.0,
        'ceiling_y_limit': 100.0,
        'center_of_mass_x': -0.45,
        'center_of_mass_y': 0.2
    }
    
    print("--- Stage-1 Fail Feedback ---")
    parts = format_task_metrics(metrics)
    for p in parts:
        print(p)
    
    # Sample metrics for a mass failure
    metrics_mass_fail = metrics.copy()
    metrics_mass_fail['structure_mass'] = 25000.0
    metrics_mass_fail['failed'] = True
    metrics_mass_fail['failure_reason'] = "Structure exceeds maximum mass: 25000.00 > 20000.0"
    
    print("\n--- Mass Failure Feedback ---")
    parts = format_task_metrics(metrics_mass_fail)
    for p in parts:
        print(p)

    # Sample metrics for a ceiling failure
    metrics_ceiling_fail = metrics.copy()
    metrics_ceiling_fail['max_y_position'] = 101.0
    metrics_ceiling_fail['failed'] = True
    metrics_ceiling_fail['failure_reason'] = "Structure hit the ceiling at y=100.0m"
    metrics_ceiling_fail['ceiling_y_limit'] = 100.0

    print("\n--- Ceiling Failure Feedback ---")
    parts = format_task_metrics(metrics_ceiling_fail)
    for p in parts:
        print(p)

    # Sample metrics for a fall failure
    metrics_fall_fail = metrics.copy()
    metrics_fall_fail['min_y_position'] = -6.0
    metrics_fall_fail['failed'] = True
    metrics_fall_fail['failure_reason'] = "Structure fell off table"

    print("\n--- Fall Failure Feedback ---")
    parts = format_task_metrics(metrics_fall_fail)
    for p in parts:
        print(p)

if __name__ == "__main__":
    test_feedback()
