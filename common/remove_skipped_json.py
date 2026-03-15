import os
import json
import argparse

'''
# 只删 skipped（原有行为）
python common/remove_skipped_json.py --dir evaluation_results

# 同时删 skipped + 未成功且 iterations < 20 的 JSON
python common/remove_skipped_json.py --dir evaluation_results --remove-incomplete-failed

# 按 21 次算「跑满」
python common/remove_skipped_json.py --dir evaluation_results --remove-incomplete-failed --min-iterations 21

# 先看会删哪些，不真删
python common/remove_skipped_json.py --dir evaluation_results --remove-incomplete-failed --dry-run
'''


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


def remove_incomplete_failed_json(root_dir, min_iterations=20, dry_run=False):
    """
    Recursively finds and removes JSON files that:
    - have "success": false, and
    - have "iterations" < min_iterations (i.e. run stopped early, e.g. due to API error).
    """
    count = 0
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    if not isinstance(data, dict):
                        continue
                    success = data.get('success', True)
                    iterations = data.get('iterations', 0)
                    if success is False and iterations < min_iterations:
                        if dry_run:
                            print(f"[dry-run] Would remove incomplete failed: {file_path} (success=false, iterations={iterations})")
                        else:
                            print(f"Removing incomplete failed file: {file_path} (success=false, iterations={iterations})")
                            os.remove(file_path)
                        count += 1
                except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
                    print(f"Error reading {file_path}: {e}")

    suffix = " (dry-run)" if dry_run else ""
    print(f"\nTotal incomplete-failed files removed{suffix}: {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Remove JSON files: skipped runs and/or incomplete failed runs (success=false, iterations < N)."
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="/home/test/test1709/THUNLP/DaVinciBench/2D_exploration/scripts/evaluation_results",
        help="Directory to search in",
    )
    parser.add_argument(
        "--skip-removed",
        action="store_true",
        help="Do not remove files with 'skipped': true (default: run both removals)",
    )
    parser.add_argument(
        "--remove-incomplete-failed",
        action="store_true",
        help="Also remove files with success=false and iterations < min-iterations",
    )
    parser.add_argument(
        "--min-iterations",
        type=int,
        default=20,
        help="When using --remove-incomplete-failed, treat runs with iterations >= this as 'complete' (default: 20)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be removed, do not delete",
    )
    args = parser.parse_args()

    if not os.path.exists(args.dir):
        print(f"Directory not found: {args.dir}")
    else:
        if not args.skip_removed:
            remove_skipped_json(args.dir)
        if args.remove_incomplete_failed:
            remove_incomplete_failed_json(args.dir, min_iterations=args.min_iterations, dry_run=args.dry_run)
