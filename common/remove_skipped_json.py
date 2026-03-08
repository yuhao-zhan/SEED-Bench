import os
import json
import argparse

def remove_skipped_json(root_dir):
    """
    Recursively finds and removes JSON files that have "skipped": true in them.
    """
    count = 0
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # Check if "skipped" is true in the json data
                    if isinstance(data, dict) and data.get('skipped') is True:
                        print(f"Removing skipped file: {file_path}")
                        os.remove(file_path)
                        count += 1
                except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
                    print(f"Error reading {file_path}: {e}")
                    
    print(f"\nTotal files removed: {count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove JSON files with 'skipped': true")
    parser.add_argument(
        "--dir", 
        type=str, 
        default="/home/test/test1709/THUNLP/DaVinciBench/2D_exploration/scripts/evaluation_results",
        help="Directory to search in"
    )
    args = parser.parse_args()
    
    if os.path.exists(args.dir):
        remove_skipped_json(args.dir)
    else:
        print(f"Directory not found: {args.dir}")
