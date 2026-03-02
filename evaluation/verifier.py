"""
Verifier module
Responsible for running code submitted by solver agent, executing simulation, and returning evaluation results
"""
import os
import sys
import tempfile
import importlib.util
import inspect
import traceback
from typing import Dict, Any, Tuple, Optional

# Add path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.simulator import Simulator, TIME_STEP, TARGET_FPS
from evaluation.prompt import parse_task_name


class CodeVerifier:
    """Code verifier"""
    
    def __init__(self, task_name: str, max_steps: int = 10000, env_overrides: Optional[Dict[str, Any]] = None):
        """
        Initialize verifier
        Args:
            task_name: Task name
            max_steps: Maximum simulation steps
            env_overrides: Optional environment overrides passed to the task's Sandbox constructor.
                Schema:
                  - terrain_config: dict
                  - physics_config: dict
        """
        self.task_name = task_name
        self.max_steps = max_steps
        self.env_overrides = env_overrides or {}
        self.simulator = None
        
        # Parse task name to get file system path
        task_path, _ = parse_task_name(task_name)
        
        # Build full path to task directory
        script_dir = os.path.dirname(os.path.dirname(__file__))
        task_dir = os.path.join(script_dir, 'tasks', task_path)
        
        if not os.path.exists(task_dir):
            raise ImportError(f"Task directory not found: {task_dir}")
        
        # Load task modules from files (handles directory names with underscores like S_01)
        self.task_module = type('TaskModule', (), {})()
        
        # Ensure task_dir is on sys.path so task modules can import each other (e.g. evaluator imports environment)
        if task_dir not in sys.path:
            sys.path.insert(0, task_dir)
        for mod_name, filename in [('environment', 'environment.py'), 
                                   ('evaluator', 'evaluator.py'),
                                   ('agent', 'agent.py'),
                                   ('renderer', 'renderer.py')]:
            file_path = os.path.join(task_dir, filename)
            if os.path.exists(file_path):
                spec = importlib.util.spec_from_file_location(mod_name, file_path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    setattr(self.task_module, mod_name, mod)
                    # Register in sys.modules so "from environment import ..." etc. work when evaluator runs
                    sys.modules[mod_name] = mod
                    spec.loader.exec_module(mod)
        
        if not hasattr(self.task_module, 'environment'):
            raise ImportError(f"Environment file not found in {task_dir}")
    
    def verify_code(self, code: str, headless: bool = True, save_gif_path: Optional[str] = None) -> Tuple[bool, float, Dict[str, Any], Optional[str]]:
        """
        Verify code: execute code, run simulation, return evaluation results
        Args:
            code: Python code submitted by solver agent
            headless: Whether to run in headless mode
            save_gif_path: If provided, will save GIF to this path
        Returns:
            Tuple[success, score, metrics, error_message]:
                - success: Whether successful
                - score: Score (0-100)
                - metrics: Evaluation metrics dictionary
                - error_message: Error message (if any)
        """
        try:
            # 1. Compile and execute code, get build_agent and agent_action functions
            code_module = self._execute_code(code)
            
            # 2. Initialize environment
            environment = self._init_environment()
            if hasattr(environment, 'remove_initial_template'):
                environment.remove_initial_template()

            # 3. Build agent
            build_agent_func = getattr(code_module, 'build_agent', None)
            if not build_agent_func:
                error_msg = "Code missing build_agent function"
                error_metrics = {
                    'error_type': 'missing_function',
                    'error_stage': 'code_parsing',
                    'error_message': error_msg
                }
                return False, 0.0, error_metrics, error_msg
            
            try:
                agent_components = build_agent_func(environment)
            except Exception as e:
                error_msg = f"Error building agent: {str(e)}\n{traceback.format_exc()}"
                error_metrics = {
                    'error_type': 'agent_building_error',
                    'error_stage': 'agent_construction',
                    'error_message': str(e),
                    'error_traceback': traceback.format_exc()
                }
                return False, 0.0, error_metrics, error_msg

            # K-05: enforce object at ground (1.8m) so it must be lifted by the mechanism
            if 'K_05' in self.task_name and hasattr(environment, 'enforce_object_at_ground'):
                environment.enforce_object_at_ground()
            
            # 4. Initialize evaluator
            evaluator = self._init_evaluator(environment)
            
            # 5. Run simulation
            success, score, metrics = self._run_simulation(
                environment, agent_components, evaluator, code_module, headless, save_gif_path
            )
            
            return success, score, metrics, None
            
        except SyntaxError as e:
            # Syntax error during code execution
            error_msg = f"Code syntax error: {str(e)}"
            error_metrics = {
                'error_type': 'syntax_error',
                'error_stage': 'code_compilation',
                'error_message': str(e),
                'error_line': getattr(e, 'lineno', None),
                'error_text': getattr(e, 'text', None)
            }
            return False, 0.0, error_metrics, error_msg
        except NameError as e:
            # Name error (e.g., undefined variable)
            error_msg = f"Code name error: {str(e)}"
            error_metrics = {
                'error_type': 'name_error',
                'error_stage': 'code_execution',
                'error_message': str(e)
            }
            return False, 0.0, error_metrics, error_msg
        except Exception as e:
            # Other execution errors
            error_msg = f"Verification process error: {str(e)}\n{traceback.format_exc()}"
            error_metrics = {
                'error_type': 'execution_error',
                'error_stage': 'verification',
                'error_message': str(e),
                'error_traceback': traceback.format_exc()
            }
            return False, 0.0, error_metrics, error_msg
    
    def _execute_code(self, code: str):
        """Execute code and return module object"""
        # First perform syntax check
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            # Include more context in the error message
            error_lines = code.split('\n')
            error_line_num = e.lineno or 0
            context_start = max(0, error_line_num - 3)
            context_end = min(len(error_lines), error_line_num + 3)
            context = '\n'.join(f"{i+1:4d}: {line}" for i, line in enumerate(error_lines[context_start:context_end], start=context_start))
            raise SyntaxError(f"Code syntax error: {e}\nCode snippet (lines {context_start+1}-{context_end}):\n{context}\n\nFull error: {e}")
        
        # Create temporary module
        spec = importlib.util.spec_from_loader("solver_code", loader=None)
        code_module = importlib.util.module_from_spec(spec)
        
        # Execute code (in isolated namespace)
        try:
            exec(code, code_module.__dict__)
        except NameError as e:
            # Check if it's a sandbox-related error
            error_msg = str(e)
            if 'sandbox' in error_msg.lower():
                raise NameError(
                    f"Code references undefined variable 'sandbox'."
                    f"Please ensure all references to sandbox are inside functions (build_agent or agent_action functions)."
                    f"\nOriginal error: {e}"
                    f"\nCode first 500 chars:\n{code[:500]}"
                )
            raise
        except Exception as e:
            raise RuntimeError(f"Error executing code: {e}\nCode first 500 chars:\n{code[:500]}")
        
        return code_module
    
    def _init_environment(self):
        """Initialize environment"""
        # Find environment class
        env_class_name = None
        if hasattr(self.task_module, 'environment'):
            for name, obj in self.task_module.environment.__dict__.items():
                if isinstance(obj, type) and 'Sandbox' in name:
                    env_class_name = name
                    break
        
        if not env_class_name:
            raise AttributeError(f"Unable to find environment class (should contain 'Sandbox')")
        
        env_class = getattr(self.task_module.environment, env_class_name)
        try:
            return env_class(**self.env_overrides)
        except TypeError:
            # Backward compatible: if environment does not accept overrides, fall back.
            return env_class()
    
    def _init_evaluator(self, environment):
        """Initialize evaluator by inspecting its __init__ signature"""
        if not hasattr(self.task_module, 'evaluator'):
            return None
        
        eval_class_name = None
        for name, obj in self.task_module.evaluator.__dict__.items():
            if isinstance(obj, type) and 'Evaluator' in name:
                eval_class_name = name
                break
        
        if not eval_class_name:
            return None
        
        eval_class = getattr(self.task_module.evaluator, eval_class_name)
        
        # Inspect __init__ signature to determine how to initialize
        try:
            sig = inspect.signature(eval_class.__init__)
            params = list(sig.parameters.keys())
            # Skip 'self' parameter
            params = [p for p in params if p != 'self']
            
            # Try different initialization patterns based on signature
            if len(params) == 0:
                # No parameters (unlikely but handle it)
                return eval_class()
            elif len(params) == 1:
                # Single parameter - likely just environment
                param_name = params[0]
                if param_name in ['sandbox', 'environment']:
                    return eval_class(environment)
                else:
                    # Try with environment anyway
                    return eval_class(environment)
            elif len(params) == 2:
                # Two parameters - check if first is terrain_bounds
                param1_name = params[0]
                param2_name = params[1]
                
                if param1_name == 'terrain_bounds':
                    # Pattern: (terrain_bounds, environment=None)
                    terrain_bounds = environment.get_terrain_bounds()
                    # Check if second parameter has default value
                    param2 = sig.parameters[param2_name]
                    if param2.default != inspect.Parameter.empty:
                        # Has default, can pass as keyword argument
                        return eval_class(terrain_bounds, environment=environment)
                    else:
                        # No default, must pass as positional
                        return eval_class(terrain_bounds, environment)
                elif param2_name in ['environment', 'sandbox']:
                    # Pattern: (start_x, target_x) or similar, but second is environment
                    # This is less common, try with environment
                    terrain_bounds = environment.get_terrain_bounds()
                    return eval_class(terrain_bounds, environment)
                else:
                    # Two parameters that are not terrain_bounds/environment
                    # Could be numeric parameters (e.g., simple task: start_x, target_x)
                    # Try to get values from environment if possible, otherwise use defaults
                    try:
                        # Try to get terrain bounds first (most common pattern)
                        terrain_bounds = environment.get_terrain_bounds()
                        return eval_class(terrain_bounds, environment)
                    except:
                        # If that fails, try numeric defaults (for simple task pattern)
                        try:
                            return eval_class(3.0, 15.0)
                        except:
                            # Last resort: try with environment only
                            return eval_class(environment)
            else:
                # More than 2 parameters - try default pattern
                terrain_bounds = environment.get_terrain_bounds()
                return eval_class(terrain_bounds, environment)
        except Exception as e:
            # Fallback to old behavior if inspection fails
            print(f"Warning: Failed to inspect evaluator signature: {e}")
            # Try common patterns
            try:
                terrain_bounds = environment.get_terrain_bounds()
                return eval_class(terrain_bounds, environment)
            except:
                return eval_class(environment)
    
    def _init_renderer(self, environment):
        """Initialize renderer"""
        if not hasattr(self.task_module, 'renderer'):
            return None
        
        renderer_class_name = None
        renderer_candidates = []
        for name, obj in self.task_module.renderer.__dict__.items():
            if (isinstance(obj, type) and 'Renderer' in name and 
                name != 'Renderer' and hasattr(obj, 'render')):
                renderer_candidates.append((name, obj))
        
        if renderer_candidates:
            task_name_lower = self.task_name.lower()
            # Prefer task-specific renderer (name contains task name)
            for name, obj in renderer_candidates:
                if task_name_lower in name.lower():
                    renderer_class_name = name
                    print(f"🔍 Found task-specific renderer: {name}")
                    break
            # If no task-specific found, use first candidate (excluding base Renderer class)
            # This is consistent with main.py logic
            if not renderer_class_name and renderer_candidates:
                for name, obj in renderer_candidates:
                    if name != 'Renderer':
                        renderer_class_name = name
                        print(f"🔍 Using candidate renderer: {name}")
                        break
                # If still none, use first one
                if not renderer_class_name:
                    renderer_class_name = renderer_candidates[0][0]
                    print(f"🔍 Using first candidate renderer: {renderer_class_name}")
        
        if renderer_class_name:
            try:
                renderer_class = getattr(self.task_module.renderer, renderer_class_name)
                renderer = renderer_class(self.simulator)
                print(f"✅ Initialized renderer: {renderer_class_name} (class: {renderer_class.__module__}.{renderer_class.__name__})")
                # Verify renderer type
                if hasattr(renderer, 'render'):
                    print(f"✅ Renderer has render method")
                else:
                    print(f"⚠️  Warning: Renderer does not have render method")
                return renderer
            except Exception as e:
                print(f"⚠️  Warning: Failed to initialize renderer {renderer_class_name}: {e}")
                import traceback
                traceback.print_exc()
                return None
        else:
            print(f"⚠️  Warning: No renderer class found (task: {self.task_name})")
            print(f"   Candidate list: {[n for n, _ in renderer_candidates] if renderer_candidates else 'None'}")
        return None
    
    def _run_simulation(self, environment, agent_components, evaluator, code_module, headless, save_gif_path=None):
        """Run simulation loop"""
        # Initialize simulator
        self.simulator = Simulator()
        # If GIF path provided, enable GIF saving
        save_gif = save_gif_path is not None
        can_display = self.simulator.init_display(headless=headless, save_gif=save_gif)
        
        # Initialize renderer (if need to save GIF or display)
        renderer = None
        if save_gif or can_display:
            renderer = self._init_renderer(environment)
        
        step_count = 0
        running = True
        camera_offset_x = 0
        
        # Get agent body (may not be needed for classify_balls)
        agent_body = None
        if isinstance(agent_components, dict):
            agent_body = agent_components.get('arm') or agent_components.get('sensor') or agent_components.get('chassis')
        else:
            agent_body = agent_components
        
        # Get agent_action function
        agent_action_func = getattr(code_module, 'agent_action', None)
        
        # For ClassifyBalls task, use special loop
        if 'classify' in self.task_name.lower():
            return self._run_classify_balls_simulation(
                environment, agent_components, evaluator, agent_action_func, headless, save_gif_path, renderer
            )
        
        # Standard simulation loop
        STABILIZATION_STEPS = 60
        last_position = None
        stuck_counter = 0
        # Unified stuck detection: Use Category1 threshold for all tasks (900 steps, 0.02m)
        # This is more lenient and reduces false positives
        STUCK_THRESHOLD = 300  # Base threshold, will be multiplied by 3
        STUCK_THRESHOLD_MULTIPLIER = 3  # Final threshold = 300 * 3 = 900 steps
        POSITION_EPSILON = 0.01  # Base epsilon, will be multiplied by 2
        POSITION_EPSILON_MULTIPLIER = 2  # Final epsilon = 0.01 * 2 = 0.02m
        
        # Render initial frame before simulation starts (to ensure at least one frame is collected)
        if save_gif and renderer and hasattr(renderer, 'render'):
            try:
                camera_offset_x = 0
                target_x_world = 0
                if agent_body:
                    target_x = agent_body.position.x * self.simulator.ppm
                    camera_offset_x = target_x - self.simulator.screen_width / 2
                elif hasattr(environment, 'get_sled_position'):
                    # E-03 Slippery World: camera follows sled
                    sled_pos = environment.get_sled_position()
                    if sled_pos:
                        camera_offset_x = sled_pos[0] * self.simulator.ppm - self.simulator.screen_width / 2
                elif hasattr(environment, 'get_body_position'):
                    # E-05 Magnet: camera follows body
                    body_pos = environment.get_body_position()
                    if body_pos:
                        camera_offset_x = body_pos[0] * self.simulator.ppm - self.simulator.screen_width / 2
                if evaluator and hasattr(evaluator, 'target_x'):
                    target_x_world = evaluator.target_x
                renderer.render(environment, agent_body, target_x_world, camera_offset_x)
                if can_display:
                    self.simulator.flip()
                self.simulator.collect_frame(0)  # Collect initial frame at step 0
            except Exception as e:
                print(f"Warning: Failed to render initial frame: {e}")
        
        # Evaluate at step 0 (design constraints only) so build-time constraints are checked before any physics step
        if evaluator and step_count == 0:
            task_lower = self.task_name.lower()
            is_category1 = 's_01' in task_lower or 's_02' in task_lower or 's_03' in task_lower or 's_04' in task_lower or 's_05' in task_lower or 's_06' in task_lower or 'category1' in task_lower or 'category_1' in task_lower
            is_e03_sled = 'e_03' in task_lower
            is_e05_magnet = 'e_05' in task_lower
            if is_category1:
                init_done, init_score, init_metrics = evaluator.evaluate(None, 0, self.max_steps)
            elif is_e05_magnet or is_e03_sled:
                # E-03: evaluator uses environment.get_sled_position(), agent_body is None
                init_done, init_score, init_metrics = evaluator.evaluate(None, 0, self.max_steps)
            elif agent_body:
                init_done, init_score, init_metrics = evaluator.evaluate(agent_body, 0, self.max_steps)
            else:
                init_done, init_score, init_metrics = False, 0.0, {}
            if init_done and init_metrics.get('failed') and init_metrics.get('failure_reason', '').startswith('Design constraint'):
                if save_gif_path and self.simulator and getattr(self.simulator, 'frames', None):
                    self.simulator.save_gif_animation(save_gif_path)
                return False, init_score, init_metrics
        
        while running and step_count < self.max_steps:
            # Handle events
            if not self.simulator.handle_events():
                running = False
                break
            
            # Agent executes action
            if agent_action_func:
                if isinstance(agent_components, dict):
                    agent_action_func(environment, agent_components, step_count)
                else:
                    agent_action_func(environment, agent_body, step_count)
            
            # Physics step
            environment.step(TIME_STEP)
            step_count += 1
            
            # Detect stuck - Unified for all tasks: Use Category1 threshold (900 steps, 0.02m)
            # This is more lenient and reduces false positives while still catching truly stuck cases
            task_lower = self.task_name.lower()
            is_category1_task = 's_01' in task_lower or 's_02' in task_lower or 's_03' in task_lower or 's_04' in task_lower or 's_05' in task_lower or 's_06' in task_lower or 'category1' in task_lower or 'category_1' in task_lower
            is_e03_sled = 'e_03' in task_lower
            is_e05_magnet = 'e_05' in task_lower
            
            # Try to get position from vehicle (Category1), sled (E-03), body (E-05), or agent_body (other tasks)
            current_pos = None
            if is_category1_task:
                vehicle_pos = environment.get_vehicle_position() if hasattr(environment, 'get_vehicle_position') else None
                if vehicle_pos:
                    current_pos = vehicle_pos
            elif is_e03_sled and hasattr(environment, 'get_sled_position'):
                sled_pos = environment.get_sled_position()
                if sled_pos:
                    current_pos = sled_pos
            elif is_e05_magnet and hasattr(environment, 'get_body_position'):
                body_pos = environment.get_body_position()
                if body_pos:
                    current_pos = body_pos
            elif agent_body:
                current_pos = (agent_body.position.x, agent_body.position.y)
            
            # Unified stuck detection for all tasks (skip for Category4/F_03: plow can be "stuck" during scoop phase;
            # skip for C_02 Lander: lander sits on ground after landing so position is constant)
            skip_stuck = ('f_03' in task_lower or 'category_4' in task_lower or 'category4' in task_lower or
                          'c_02' in task_lower or ('category_5_02' in task_lower) or
                          'c_03' in task_lower or ('category_5_03' in task_lower) or
                          'e_04' in task_lower)
            if current_pos and not skip_stuck:
                if step_count > STABILIZATION_STEPS and last_position is not None:
                    dx = abs(current_pos[0] - last_position[0])
                    dy = abs(current_pos[1] - last_position[1])
                    # Use Category1 threshold: 0.02m (more lenient)
                    if dx < POSITION_EPSILON * POSITION_EPSILON_MULTIPLIER and dy < POSITION_EPSILON * POSITION_EPSILON_MULTIPLIER:
                        stuck_counter += 1
                        # Use Category1 threshold: 900 steps (more lenient)
                        if stuck_counter >= STUCK_THRESHOLD * STUCK_THRESHOLD_MULTIPLIER:
                            print(f"Detected stuck at step {step_count} (position change < {POSITION_EPSILON * POSITION_EPSILON_MULTIPLIER}m for {STUCK_THRESHOLD * STUCK_THRESHOLD_MULTIPLIER} steps), stopping simulation")
                            running = False
                            break
                    else:
                        stuck_counter = 0
            if current_pos:
                last_position = current_pos
                
                # Check if vehicle/agent fell (failure condition, not stuck detection)
                if is_category1_task:
                    if current_pos[1] < 0.5:
                        running = False
                        break
                elif agent_body:
                    # Detect anomalies for non-Category1 tasks
                    import math
                    speed = math.sqrt(agent_body.linearVelocity.x**2 + agent_body.linearVelocity.y**2)
                    if speed > 20:
                        running = False
                        break
                    
                    if agent_body.position.y < -10:
                        running = False
                        break
            
            # Render
            if (save_gif or can_display) and renderer and hasattr(renderer, 'render'):
                # Camera follow: agent_body, or sled for E-03
                if agent_body:
                    target_x = agent_body.position.x * self.simulator.ppm
                    camera_offset_x = target_x - self.simulator.screen_width / 2
                elif is_e03_sled and hasattr(environment, 'get_sled_position'):
                    sled_pos = environment.get_sled_position()
                    if sled_pos:
                        camera_offset_x = sled_pos[0] * self.simulator.ppm - self.simulator.screen_width / 2
                    else:
                        camera_offset_x = 0
                elif is_e05_magnet and hasattr(environment, 'get_body_position'):
                    body_pos = environment.get_body_position()
                    if body_pos:
                        camera_offset_x = body_pos[0] * self.simulator.ppm - self.simulator.screen_width / 2
                    else:
                        camera_offset_x = 0
                else:
                    camera_offset_x = 0
                
                # Get target position (for rendering)
                target_x_world = None
                if evaluator and hasattr(evaluator, 'target_x'):
                    target_x_world = evaluator.target_x
                elif evaluator and hasattr(evaluator, 'get_task_description'):
                    task_info = evaluator.get_task_description()
                    target_x_world = task_info.get('target_position', 0)
                
                # Render (even if agent_body is None, render environment)
                try:
                    # Verify renderer type (only for basic task)
                    if 'basic' in self.task_name.lower():
                        renderer_type = type(renderer).__name__
                        if renderer_type != 'BasicRenderer':
                            print(f"⚠️  Warning: Using wrong renderer type: {renderer_type}, should be BasicRenderer")
                    renderer.render(environment, agent_body, target_x_world or 0, camera_offset_x)
                except Exception as e:
                    print(f"Rendering error: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Refresh display
                if can_display:
                    self.simulator.flip()
                    self.simulator.tick()
                
                # Collect frames after rendering (only if rendering succeeded)
                if save_gif:
                    self.simulator.collect_frame(step_count)
            elif save_gif:
                # If no renderer but save_gif is enabled, try to collect frame anyway
                # This handles cases where renderer failed to initialize but we still want to save
                self.simulator.collect_frame(step_count)
            
            # Evaluate
            # For Category1 tasks (S_01-S_06), evaluator doesn't need agent_body (tracks structure/vehicle via environment)
            # For K_03 (gripper), evaluate every 10 steps so success (hold 80 steps) is detected before object may fall
            # For C_03 (seeker), evaluate every 10 steps to detect "target lost" (distance > 6m) promptly
            # For C_02 (lander), evaluate every step so landing (and success/failure) is detected immediately
            task_lower = self.task_name.lower()
            is_category2_k03 = 'k_03' in task_lower or ('category2' in task_lower and 'kinematics' in task_lower)
            is_category5_c03 = 'c_03' in task_lower or ('category_5_03' in task_lower)
            is_category5_c02 = 'c_02' in task_lower or ('category_5_02' in task_lower)
            is_e05_magnet = 'e_05' in task_lower
            eval_interval = 1 if (is_category5_c02 or is_e05_magnet) else (10 if (is_category2_k03 or is_category5_c03) else 100)
            if step_count % eval_interval == 0 and evaluator:
                # Check for Category1 tasks (case-insensitive) or E-03 (sled, no agent_body)
                is_category1 = 's_01' in task_lower or 's_02' in task_lower or 's_03' in task_lower or 's_04' in task_lower or 's_05' in task_lower or 's_06' in task_lower or 'category1' in task_lower or 'category_1' in task_lower
                if is_category1:
                    # Category1 evaluators don't use agent_body - they get info from environment
                    should_stop, score, metrics = evaluator.evaluate(None, step_count, self.max_steps)
                elif is_e05_magnet:
                    should_stop, score, metrics = evaluator.evaluate(None, step_count, self.max_steps)
                elif is_e03_sled:
                    # E-03: evaluator uses environment.get_sled_position()
                    should_stop, score, metrics = evaluator.evaluate(None, step_count, self.max_steps)
                elif agent_body:
                    should_stop, score, metrics = evaluator.evaluate(agent_body, step_count, self.max_steps)
                else:
                    should_stop, score, metrics = False, 0.0, {}
                
                if should_stop and metrics.get('success'):
                    # Render and collect final frame before saving GIF
                    if (save_gif or can_display) and renderer and hasattr(renderer, 'render'):
                        if agent_body:
                            target_x = agent_body.position.x * self.simulator.ppm
                            camera_offset_x = target_x - self.simulator.screen_width / 2
                        elif is_e03_sled and hasattr(environment, 'get_sled_position'):
                            sled_pos = environment.get_sled_position()
                            camera_offset_x = (sled_pos[0] * self.simulator.ppm - self.simulator.screen_width / 2) if sled_pos else 0
                        else:
                            camera_offset_x = 0
                        target_x_world = None
                        if evaluator and hasattr(evaluator, 'target_x'):
                            target_x_world = evaluator.target_x
                        try:
                            renderer.render(environment, agent_body, target_x_world or 0, camera_offset_x)
                        except Exception as e:
                            print(f"Rendering error: {e}")
                    # Collect final frame
                    if save_gif:
                        self.simulator.collect_frame(step_count)
                    # Save GIF before returning (important: save current state)
                    if save_gif_path and self.simulator:
                        self.simulator.save_gif_animation(save_gif_path)
                    return True, score, metrics
                elif should_stop and metrics.get('failed'):
                    # Render and collect final frame before saving GIF
                    if (save_gif or can_display) and renderer and hasattr(renderer, 'render'):
                        if agent_body:
                            target_x = agent_body.position.x * self.simulator.ppm
                            camera_offset_x = target_x - self.simulator.screen_width / 2
                        elif is_e03_sled and hasattr(environment, 'get_sled_position'):
                            sled_pos = environment.get_sled_position()
                            camera_offset_x = (sled_pos[0] * self.simulator.ppm - self.simulator.screen_width / 2) if sled_pos else 0
                        else:
                            camera_offset_x = 0
                        target_x_world = None
                        if evaluator and hasattr(evaluator, 'target_x'):
                            target_x_world = evaluator.target_x
                        try:
                            renderer.render(environment, agent_body, target_x_world or 0, camera_offset_x)
                        except Exception as e:
                            print(f"Rendering error: {e}")
                    # Collect final frame
                    if save_gif:
                        self.simulator.collect_frame(step_count)
                    # Save GIF before returning (even if failed)
                    if save_gif_path and self.simulator:
                        self.simulator.save_gif_animation(save_gif_path)
                    return False, score, metrics
        
        # Final evaluation
        # For Category1 (S_01-S_06) and E-03 (sled), evaluator uses environment; agent_body may be None
        if evaluator:
            task_lower = self.task_name.lower()
            is_category1_final = 's_01' in task_lower or 's_02' in task_lower or 's_03' in task_lower or 's_04' in task_lower or 's_05' in task_lower or 's_06' in task_lower or 'category1' in task_lower or 'category_1' in task_lower
            is_e03_final = 'e_03' in task_lower or ('category6' in task_lower and 'exotic' in task_lower)
            if is_category1_final or is_e03_final:
                final_should_stop, final_score, final_metrics = evaluator.evaluate(
                    None, step_count, self.max_steps
                )
            elif agent_body:
                final_should_stop, final_score, final_metrics = evaluator.evaluate(
                    agent_body, step_count, self.max_steps
                )
            else:
                final_should_stop, final_score, final_metrics = False, 0.0, {}
            
            # Save GIF
            if save_gif_path and self.simulator:
                self.simulator.save_gif_animation(save_gif_path)
            
            return final_metrics.get('success', False), final_score, final_metrics
        
        # Save GIF (even without evaluator)
        if save_gif_path and self.simulator:
            self.simulator.save_gif_animation(save_gif_path)
        
        return False, 0.0, {}
    
    def _run_classify_balls_simulation(self, environment, agent_components, evaluator, 
                                       agent_action_func, headless, save_gif_path=None, renderer=None):
        """Run simulation loop for ClassifyBalls task"""
        step_count = 0
        running = True
        camera_offset_x = 0
        save_gif = save_gif_path is not None
        can_display = self.simulator.can_display if hasattr(self.simulator, 'can_display') else False
        
        while running and step_count < self.max_steps:
            # Handle events
            if not self.simulator.handle_events():
                running = False
                break
            
            # Spawn balls
            if environment.balls_spawned < environment.balls_to_spawn:
                environment.ball_spawn_timer += 1
                spawn_interval = environment.ball_spawn_interval_base
                if environment.ball_spawn_timer >= spawn_interval:
                    color = environment.ball_spawn_order[environment.balls_spawned]
                    ball = environment.spawn_ball(color)
                    environment.ball_spawn_timer = 0
            
            # Agent executes action
            if agent_action_func:
                agent_action_func(environment, agent_components, step_count)
            
            # Physics step
            environment.step(TIME_STEP)
            step_count += 1
            
            # Render
            if (save_gif or can_display) and renderer and hasattr(renderer, 'render'):
                # Camera fixed at conveyor center
                target_x = (environment.conveyor_start_x + environment.conveyor_end_x) / 2 * self.simulator.ppm
                camera_offset_x = target_x - self.simulator.screen_width / 2
                
                try:
                    renderer.render(environment, agent_components, camera_offset_x)
                except Exception as e:
                    print(f"Rendering error: {e}")
                
                # Refresh display
                if can_display:
                    self.simulator.flip()
                    self.simulator.tick()
            
            # Collect frames
            if save_gif:
                self.simulator.collect_frame(step_count)
            
            # Evaluate
            if step_count % 100 == 0 and evaluator:
                should_stop, score, metrics = evaluator.evaluate(step_count, self.max_steps)
                
                if should_stop and metrics.get('success'):
                    return True, score, metrics
                elif should_stop:
                    return False, score, metrics
        
        # Final evaluation
        if evaluator:
            final_should_stop, final_score, final_metrics = evaluator.evaluate(step_count, self.max_steps)
            
            # Save GIF
            if save_gif_path and self.simulator:
                self.simulator.save_gif_animation(save_gif_path)
            
            return final_metrics.get('success', False), final_score, final_metrics
        
        # Save GIF (even without evaluator)
        if save_gif_path and self.simulator:
            self.simulator.save_gif_animation(save_gif_path)
        
        return False, 0.0, {}
    
    def cleanup(self):
        """Cleanup resources"""
        if self.simulator:
            self.simulator.quit()
