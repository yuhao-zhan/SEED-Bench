import os
import shutil

def remove_pycache(root_dir):
    """
    Recursively removes all __pycache__ directories starting from root_dir.
    """
    for root, dirs, files in os.walk(root_dir):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            print(f"Removing: {pycache_path}")
            try:
                shutil.rmtree(pycache_path)
                # Remove from dirs list so os.walk doesn't try to visit it
                dirs.remove('__pycache__')
            except Exception as e:
                print(f"Error removing {pycache_path}: {e}")

if __name__ == "__main__":
    # Get the project root directory (two levels up from this script)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    print(f"Cleaning __pycache__ in: {project_root}")
    remove_pycache(project_root)
    print("Cleanup complete.")
