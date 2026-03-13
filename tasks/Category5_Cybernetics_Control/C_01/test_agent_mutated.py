import importlib.util
import os
import sys

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from evaluation.verifier import CodeVerifier

# Load stages from same task directory
_task_dir = os.path.dirname(os.path.abspath(__file__))
_stages_path = os.path.join(_task_dir, "stages.py")
spec = importlib.util.spec_from_file_location("c01_stages", _stages_path)
stages_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stages_mod)
get_stages = getattr(stages_mod, "get_stages")


def main():
    task_name = "Category5_Cybernetics_Control/C_01"
    max_steps = 10000
    agent_path = os.path.join(os.path.dirname(__file__), "agent.py")
    with open(agent_path, "r") as f:
        code = f.read()

    # CRITICAL: We only want to test the INITIAL solution (build_agent/agent_action)
    # We remove the stage-specific functions from the code string to ensure verifier 
    # uses the default one, or we just rely on CodeVerifier picking the main ones.
    
    stages = get_stages()
    results = []

    # Skip the "Initial" stage because that's the one it's supposed to pass
    mutated_stages = [s for s in stages if s["name"] != "Initial"]

    print(f"Running INITIAL reference solution on {len(mutated_stages)} mutated stages...")
    print("Expected: FAIL (Original solution has no swing-up logic)")
    print("-" * 60)

    for stage in mutated_stages:
        stage_name = stage["name"]
        config = stage.get("config_overrides", {})
        
        # verifier expects terrain_config and physics_config
        env_overrides = {
            "physics_config": {
                "gravity": config.get("gravity", 9.8),
                "pole_length": config.get("pole_length", 2.0),
                "pole_damping": config.get("pole_damping", 0.0),
                "pole_start_angle": config.get("pole_start_angle", 0.0),
                "sensor_delay_steps": config.get("sensor_delay_steps", 0)
            }
        }
        
        verifier = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=env_overrides)
        
        # We ensure it only uses 'build_agent' and 'agent_action'
        # The CodeVerifier.verify_code logic defaults to these.
        success, score, metrics, error = verifier.verify_code(code, headless=True, save_gif_path=None)
        
        results.append((stage_name, success, score, metrics.get("failure_reason"), error))
        print(f"{stage_name}: success={success}, score={score:.2f}")
        if metrics.get("failure_reason"):
            print(f"  failure_reason: {metrics['failure_reason']}")

    print("\n--- Summary ---")
    all_failed = all(not r[1] for r in results)
    for stage_name, success, score, reason, err in results:
        status = "PASS" if success else "FAIL"
        print(f"  {stage_name}: {status} (score={score:.2f})")
    
    if all_failed:
        print("\nSUCCESS: Initial reference solution FAILED on all mutated stages as expected.")
        return 0
    else:
        print("\nWARNING: Initial reference solution passed on some stages. Mutation might be too weak.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
