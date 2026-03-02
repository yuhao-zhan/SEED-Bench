"""
Feedback generation module
Generate structured feedback information based on evaluation results
"""
import os
import sys
import importlib.util
from typing import Dict, Any, Optional

# Add path for task modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _get_task_feedback_module(task_name: str):
    """
    Dynamically import task-specific feedback module
    Args:
        task_name: Task name (can be in various formats like 'category_1_01', 'Category1_Statics_Equilibrium/S_01', etc.)
    Returns:
        Task feedback module or None if not found
    """
    try:
        # Parse task name to get file system path (handles various formats)
        from evaluation.prompt import parse_task_name
        
        task_path, _ = parse_task_name(task_name)
        
        # Build full path to feedback.py file
        script_dir = os.path.dirname(os.path.dirname(__file__))
        feedback_file = os.path.join(script_dir, 'tasks', task_path, 'feedback.py')
        
        if not os.path.exists(feedback_file):
            # Feedback file doesn't exist for this task
            return None
        
        # Load module from file using importlib (handles directory names with underscores like S_01)
        spec = importlib.util.spec_from_file_location("task_feedback", feedback_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        else:
            return None
    except (ImportError, ModuleNotFoundError, ValueError, Exception) as e:
        # If parsing fails or import fails, return None
        return None


def format_feedback(metrics: Dict[str, Any], score: float, success: bool, failed: bool, 
                   failure_reason: str = None, iteration: int = 0, error: Optional[str] = None,
                   task_name: str = None, include_suggestions: bool = False) -> str:
    """
    Generate feedback text based on evaluation metrics
    Args:
        metrics: Evaluation metrics dictionary
        score: Score (0-100)
        success: Whether successful
        failed: Whether failed
        failure_reason: Failure reason
        iteration: Current iteration number
        error: Error message if code execution failed
        task_name: Task name for loading task-specific feedback
        include_suggestions: Whether to include improvement suggestions (only for sys_feedback mode)
    Returns:
        str: Formatted feedback text
    """
    feedback_parts = []
    
    feedback_parts.append(f"## Iteration {iteration} Evaluation Results\n")
    
    # Code execution status section
    if error:
        feedback_parts.append("## Code Execution Status\n")
        feedback_parts.append("❌ **Code execution failed**\n\n")
        
        # Parse error type
        error_lower = error.lower()
        if "syntax error" in error_lower or "invalid syntax" in error_lower:
            error_type = "Syntax Error"
            feedback_parts.append(f"**Error Type**: {error_type}\n")
            feedback_parts.append("The generated code contains syntax errors that prevent it from being executed.\n")
        elif "name 'sandbox' is not defined" in error_lower or "nameerror" in error_lower:
            error_type = "Name Error"
            feedback_parts.append(f"**Error Type**: {error_type}\n")
            feedback_parts.append("The code references undefined variables. Ensure all code is inside functions.\n")
        elif "error building agent" in error_lower or "valueerror" in error_lower:
            error_type = "Agent Building Error"
            feedback_parts.append(f"**Error Type**: {error_type}\n")
            feedback_parts.append("The code executed but failed during agent construction (e.g., constraint violations).\n")
        elif "runtime error" in error_lower:
            error_type = "Runtime Error"
            feedback_parts.append(f"**Error Type**: {error_type}\n")
            feedback_parts.append("The code executed but encountered a runtime error during execution.\n")
        else:
            error_type = "Execution Error"
            feedback_parts.append(f"**Error Type**: {error_type}\n")
            feedback_parts.append("The code failed during execution.\n")
        
        # Full error details
        feedback_parts.append("\n**Error Details**:\n")
        feedback_parts.append("```")
        # Truncate very long errors, but keep important parts
        error_lines = error.split('\n')
        # Keep first 30 lines (usually contains the most important info)
        if len(error_lines) > 30:
            feedback_parts.append('\n'.join(error_lines[:30]))
            feedback_parts.append(f"\n... (truncated, {len(error_lines) - 30} more lines)")
        else:
            feedback_parts.append(error)
        feedback_parts.append("```\n")
        
        feedback_parts.append(f"\n**Score**: {score:.1f}/100 (Code execution failed)\n")
        
    elif success:
        feedback_parts.append("✅ **Task completed successfully!**\n")
        feedback_parts.append(f"**Score**: {score:.1f}/100\n")
    elif failed:
        feedback_parts.append(f"❌ **Task failed**: {failure_reason}\n")
        feedback_parts.append(f"**Score**: {score:.1f}/100\n")
    else:
        feedback_parts.append("⚠️ **Task not completed**\n")
        feedback_parts.append(f"**Score**: {score:.1f}/100\n")
    
    # Get task-specific feedback module once (if needed)
    task_feedback_module = None
    if task_name:
        task_feedback_module = _get_task_feedback_module(task_name)
    
    # Task execution results section (only if code executed successfully)
    if not error and metrics:
        feedback_parts.append("\n## Task Execution Results\n")
        
        # Get task-specific metrics formatting
        task_metric_parts = []
        if task_feedback_module and hasattr(task_feedback_module, 'format_task_metrics'):
            try:
                task_metric_parts = task_feedback_module.format_task_metrics(metrics)
            except Exception as e:
                # If task-specific metrics formatting fails, log error and continue without it
                import sys
                print(f"⚠️  Warning: Task-specific metrics formatting failed for {task_name}: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                pass
        
        # Add task-specific metrics if available
        if task_metric_parts:
            feedback_parts.extend(task_metric_parts)
        else:
            # Fallback: if no task-specific formatting, just show basic info
            feedback_parts.append("**Metrics available but task-specific formatting not found**")
    
    # Add improvement suggestions (only if include_suggestions is True)
    if include_suggestions:
        feedback_parts.append("\n## Improvement Suggestions\n")
        
        # Generic error suggestions (applicable to all tasks)
        if error:
            error_lower = error.lower()
            if "syntax error" in error_lower or "invalid syntax" in error_lower:
                feedback_parts.append("- Fix syntax errors in the code (check for missing parentheses, brackets, or quotes)")
                feedback_parts.append("- Ensure code blocks are properly closed")
                feedback_parts.append("- Remove any markdown formatting or non-code text from the output")
            elif "name 'sandbox' is not defined" in error_lower:
                feedback_parts.append("- Move all code that uses 'sandbox' inside the build_agent function")
                feedback_parts.append("- Do not use 'sandbox' variable at module level")
            else:
                feedback_parts.append("- Review the error details above to identify the specific issue")
                feedback_parts.append("- Ensure code follows the required function structure (build_agent and optionally agent_action)")
        
        # Try to get task-specific suggestions
        task_suggestions = []
        if task_feedback_module and hasattr(task_feedback_module, 'get_improvement_suggestions'):
            try:
                task_suggestions = task_feedback_module.get_improvement_suggestions(
                    metrics, score, success, failed, failure_reason, error
                )
            except Exception as e:
                # If task-specific feedback fails, continue without it
                pass
        
        # Add task-specific suggestions
        if task_suggestions:
            for suggestion in task_suggestions:
                feedback_parts.append(suggestion)
        elif not error:
            # Fallback: if no task-specific suggestions and no error, provide generic guidance
            feedback_parts.append("- Review the metrics above to identify areas for improvement")
    
    return "\n".join(feedback_parts)
