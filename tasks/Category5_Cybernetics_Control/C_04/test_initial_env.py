import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from main import TaskRunner
from tasks.Category5_Cybernetics_Control.C_04.environment import MAX_STEPS

def test_initial():
    task_name = "Category5_Cybernetics_Control.C_04"
    task_module = __import__(f"tasks.{task_name}", fromlist=["agent", "environment", "evaluator"])
    runner = TaskRunner(task_name, task_module)
    result = runner.run(headless=True, max_steps=MAX_STEPS)
    if result:
        score, metrics = result
        print(f"Initial Result: Score={score}, Success={metrics.get('success')}")
        if not metrics.get('success'):
            print(f"Failure Reason: {metrics.get('failure_reason')}")
            print(f"Metrics: x={metrics.get('agent_x')}, y={metrics.get('agent_y')}, steps={metrics.get('step_count')}")

if __name__ == "__main__":
    test_initial()
