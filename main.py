#!/usr/bin/env python3
"""
DaVinciBench top-level script
Unified call to all task modules, run simulation and output results
"""
import os
import sys
import math

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from common.simulator import Simulator, TIME_STEP, TARGET_FPS
from common.renderer import Renderer


class TaskRunner:
    """Task runner base class"""
    
    def __init__(self, task_name, task_module):
        self.task_name = task_name
        self.task_module = task_module
        self.simulator = None
        self.renderer = None
        self.environment = None
        self.evaluator = None
        self.agent_components = None
        
    def run(self, headless=False, max_steps=None, save_gif=False, env_overrides=None):
        """
        Run task
        Args:
            headless: Whether headless mode
            max_steps: Maximum steps
            save_gif: Whether to save GIF
            env_overrides: Optional dict with terrain_config and/or physics_config for the environment
        """
        if max_steps is None:
            from evaluation.utils import get_max_steps_for_task
            max_steps = get_max_steps_for_task(self.task_name)
        
        # Initialize simulator (D_03: higher PPM so objects draw larger in GIF)
        from common.simulator import PPM
        ppm = 32 if 'D_03' in self.task_name else PPM
        self.simulator = Simulator(ppm=ppm)
        can_display = self.simulator.init_display(headless=headless, save_gif=save_gif)
        
        # Initialize environment
        # Get environment class name
        env_class_name = None
        if hasattr(self.task_module, 'environment'):
            for name, obj in self.task_module.environment.__dict__.items():
                if isinstance(obj, type) and 'Sandbox' in name:
                    env_class_name = name
                    break
        
        if env_class_name:
            env_class = getattr(self.task_module.environment, env_class_name)
            overrides = dict(env_overrides) if env_overrides else {}
            # E-01: no demonstrators so only agent structure is evaluated (demonstrators would fly out)
            if 'E_01' in self.task_name:
                tc = overrides.get('terrain_config') or {}
                tc = dict(tc) if isinstance(tc, dict) else {}
                tc['no_demonstrators'] = True
                overrides['terrain_config'] = tc
            self.environment = env_class(
                terrain_config=overrides.get('terrain_config'),
                physics_config=overrides.get('physics_config'),
            )
        else:
            raise AttributeError(f"Could not find environment class (should contain 'Sandbox')")
        
        # Build Agent
        try:
            if hasattr(self.task_module.agent, 'build_agent'):
                self.agent_components = self.task_module.agent.build_agent(self.environment)
            else:
                raise AttributeError("Agent module missing build_agent function")
        except Exception as e:
            print(f"Agent build failed: {e}")
            return None

        # K-05: enforce object at ground (1.8m) so it must be lifted by the mechanism
        if 'K_05' in self.task_name and hasattr(self.environment, 'enforce_object_at_ground'):
            self.environment.enforce_object_at_ground()

        # Initialize evaluator
        if hasattr(self.task_module, 'evaluator'):
            eval_class_name = None
            for name, obj in self.task_module.evaluator.__dict__.items():
                if isinstance(obj, type) and 'Evaluator' in name:
                    eval_class_name = name
                    break
            
            if eval_class_name:
                eval_class = getattr(self.task_module.evaluator, eval_class_name)
                # Initialize evaluator based on task type
                if 'classify' in self.task_name.lower():
                    self.evaluator = eval_class(self.environment)
                elif 'control_aware' in self.task_name.lower():
                    terrain_bounds = self.environment.get_terrain_bounds()
                    self.evaluator = eval_class(terrain_bounds, environment=self.environment)
                elif 'basic' in self.task_name.lower():
                    terrain_bounds = self.environment.get_terrain_bounds()
                    self.evaluator = eval_class(terrain_bounds, environment=self.environment)
                elif 'simple' in self.task_name.lower():
                    self.evaluator = eval_class(3.0, 15.0)  # Simple task start and target positions
                elif 'Category1' in self.task_name or 'S_01' in self.task_name or 'S_02' in self.task_name or 'S_03' in self.task_name or 'S_04' in self.task_name or 'S_05' in self.task_name or 'S_06' in self.task_name:
                    # Category 1 tasks need terrain_bounds and environment
                    terrain_bounds = self.environment.get_terrain_bounds()
                    self.evaluator = eval_class(terrain_bounds, environment=self.environment)
                elif 'Category2' in self.task_name or 'K_01' in self.task_name or 'K_02' in self.task_name or 'K_03' in self.task_name or 'K_04' in self.task_name or 'K_05' in self.task_name or 'K_06' in self.task_name:
                    # Category 2 tasks need terrain_bounds and environment
                    terrain_bounds = self.environment.get_terrain_bounds()
                    self.evaluator = eval_class(terrain_bounds, environment=self.environment)
                elif 'Category3' in self.task_name or 'D_01' in self.task_name or 'D_02' in self.task_name or 'D_03' in self.task_name or 'D_04' in self.task_name or 'D_05' in self.task_name or 'D_06' in self.task_name:
                    # Category 3 (Dynamics) tasks need terrain_bounds and environment
                    terrain_bounds = self.environment.get_terrain_bounds()
                    self.evaluator = eval_class(terrain_bounds, environment=self.environment)
                elif 'Category4' in self.task_name or 'F_01' in self.task_name or 'F_02' in self.task_name or 'F_03' in self.task_name or 'F_04' in self.task_name or 'F_05' in self.task_name or 'F_06' in self.task_name:
                    # Category 4 (Granular/Fluid) tasks need terrain_bounds and environment
                    terrain_bounds = self.environment.get_terrain_bounds()
                    self.evaluator = eval_class(terrain_bounds, environment=self.environment)
                elif 'Category5' in self.task_name or 'C_01' in self.task_name or 'C_05' in self.task_name:
                    # Category 5 (Cybernetics/Control) e.g. C_01 Cart-Pole, C_05 Logic Lock
                    terrain_bounds = self.environment.get_terrain_bounds()
                    self.evaluator = eval_class(terrain_bounds, environment=self.environment)
                elif 'Category6' in self.task_name or 'E_01' in self.task_name or 'E_02' in self.task_name:
                    # Category 6 (Exotic Physics) e.g. E_01 Inverted Gravity, E_02 Thick Air
                    terrain_bounds = self.environment.get_terrain_bounds()
                    self.evaluator = eval_class(terrain_bounds, environment=self.environment)
                else:
                    self.evaluator = eval_class(self.environment)
            else:
                print("Warning: Could not find evaluator class")
        
        # Print task information
        if self.evaluator and hasattr(self.evaluator, 'get_task_description'):
            task_info = self.evaluator.get_task_description()
            print("\n=== Task Information ===")
            print(f"Task: {task_info.get('task', 'Unknown')}")
            print(f"Description: {task_info.get('description', 'Unknown')}")
            if 'start_position' in task_info:
                print(f"Start position: x={task_info['start_position']}m")
            if 'target_position' in task_info:
                print(f"Target position: x={task_info['target_position']}m")
            print("=======================\n")
        
        # Initialize renderer
        self.renderer = None
        if can_display and hasattr(self.task_module, 'renderer'):
            renderer_class_name = None
            # Find renderer class (exclude base Renderer, prioritize task-specific)
            renderer_candidates = []
            for name, obj in self.task_module.renderer.__dict__.items():
                if (isinstance(obj, type) and 'Renderer' in name and 
                    name != 'Renderer' and hasattr(obj, 'render')):
                    renderer_candidates.append((name, obj))
            
            # Prioritize task-specific renderer (name contains task name or not base class)
            if renderer_candidates:
                # Try to find renderer containing task name
                task_name_lower = self.task_name.lower()
                for name, obj in renderer_candidates:
                    if task_name_lower in name.lower() or name != 'Renderer':
                        renderer_class_name = name
                        break
                # If not found, use first candidate
                if not renderer_class_name and renderer_candidates:
                    renderer_class_name = renderer_candidates[0][0]
            
            if renderer_class_name:
                try:
                    renderer_class = getattr(self.task_module.renderer, renderer_class_name)
                    self.renderer = renderer_class(self.simulator)
                    print(f"✅ Initialized renderer: {renderer_class_name}")
                except Exception as e:
                    print(f"Warning: Could not initialize renderer {renderer_class_name}: {e}")
                    import traceback
                    traceback.print_exc()
                    self.renderer = None
            else:
                print("Warning: Task-specific renderer class not found")
        
        # Run simulation loop
        return self._run_simulation_loop(max_steps, can_display, save_gif)
    
    def _run_simulation_loop(self, max_steps, can_display, save_gif):
        """Run simulation loop"""
        step_count = 0
        running = True
        camera_offset_x = 0
        
        # Get agent main body (for camera follow and evaluation)
        agent_body = None
        if isinstance(self.agent_components, dict):
            # ClassifyBalls or ControlAware task returns dictionary
            agent_body = self.agent_components.get('arm') or self.agent_components.get('sensor') or self.agent_components.get('bob')
        else:
            # Basic and Simple tasks directly return body
            agent_body = self.agent_components
        
        # For ClassifyBalls, need special handling
        if 'classify' in self.task_name.lower():
            # ClassifyBalls task needs special handling
            return self._run_classify_balls_loop(max_steps, can_display, save_gif)
        
        # For ControlAware, use agent_components for evaluation
        is_control_aware = 'control_aware' in self.task_name.lower()
        
        # Evaluate at step 0 so design constraints (build zone, mass) are checked before any physics step
        if self.evaluator and step_count == 0:
            if 'S_01' in self.task_name or 'Category1' in self.task_name:
                init_done, init_score, init_metrics = self.evaluator.evaluate(None, 0, max_steps)
            elif 'Category4' in self.task_name or 'F_01' in self.task_name or 'F_02' in self.task_name or 'F_03' in self.task_name or 'F_04' in self.task_name or 'F_05' in self.task_name or 'F_06' in self.task_name:
                init_done, init_score, init_metrics = self.evaluator.evaluate(agent_body, 0, max_steps)
            elif 'Category2' in self.task_name or 'K_01' in self.task_name or 'K_02' in self.task_name or 'K_03' in self.task_name or 'K_04' in self.task_name or 'K_05' in self.task_name or 'K_06' in self.task_name:
                init_done, init_score, init_metrics = self.evaluator.evaluate(agent_body, 0, max_steps)
            elif 'Category3' in self.task_name or 'D_01' in self.task_name or 'D_02' in self.task_name or 'D_03' in self.task_name or 'D_04' in self.task_name or 'D_05' in self.task_name or 'D_06' in self.task_name:
                init_done, init_score, init_metrics = self.evaluator.evaluate(agent_body, 0, max_steps)
            elif is_control_aware:
                init_done, init_score, init_metrics = self.evaluator.evaluate(self.agent_components, 0, max_steps)
            elif 'Category6' in self.task_name or 'E_02' in self.task_name:
                init_done, init_score, init_metrics = self.evaluator.evaluate(None, 0, max_steps)
            elif agent_body:
                init_done, init_score, init_metrics = self.evaluator.evaluate(agent_body, 0, max_steps)
            else:
                init_done, init_score, init_metrics = False, 0.0, {}
            if init_done and init_metrics.get('failed') and (init_metrics.get('failure_reason') or '').startswith('Design constraint'):
                return init_score, init_metrics
        
        # Initial stabilization period
        STABILIZATION_STEPS = 60
        last_position = None
        stuck_counter = 0
        STUCK_THRESHOLD = 300
        POSITION_EPSILON = 0.01
        
        while running and step_count < max_steps:
            # Handle events
            if not self.simulator.handle_events():
                running = False
                break
            
            # Agent executes action
            if hasattr(self.task_module.agent, 'agent_action'):
                if hasattr(self.environment, '_current_step'):
                    self.environment._current_step = step_count
                if isinstance(self.agent_components, dict):
                    self.task_module.agent.agent_action(
                        self.environment, self.agent_components, step_count
                    )
                else:
                    self.task_module.agent.agent_action(
                        self.environment, agent_body, step_count
                    )
            
            # Physics step
            self.environment.step(TIME_STEP)
            step_count += 1
            
            # Detect stuck
            # For S_01, track vehicle instead of agent_body
            if 'S_01' in self.task_name or 'Category1' in self.task_name:
                vehicle_pos = self.environment.get_vehicle_position() if hasattr(self.environment, 'get_vehicle_position') else None
                if vehicle_pos:
                    current_pos = vehicle_pos
                    if step_count > STABILIZATION_STEPS and last_position is not None:
                        dx = abs(current_pos[0] - last_position[0])
                        dy = abs(current_pos[1] - last_position[1])
                        # For bridge task, vehicle may slow down, so use larger threshold
                        if dx < POSITION_EPSILON * 2 and dy < POSITION_EPSILON * 2:
                            stuck_counter += 1
                            # Increase threshold for bridge (vehicle may slow on bridge)
                            if stuck_counter >= STUCK_THRESHOLD * 3:
                                print(f"Detected Vehicle stuck at x={current_pos[0]:.2f}m, stopping simulation")
                                running = False
                                break
                        else:
                            stuck_counter = 0
                    last_position = current_pos
                    
                    # Check if vehicle fell
                    if current_pos[1] < 0.5:
                        print(f"Vehicle fell into water, stopping simulation")
                        running = False
                        break
            elif agent_body:
                current_pos = (agent_body.position.x, agent_body.position.y)
                # K_03/K_04/K_05/K_06/D_01: skip agent stuck detection
                skip_stuck = ('K_03' in self.task_name or 'K_04' in self.task_name or 'K_05' in self.task_name or
                              'K_06' in self.task_name or 'D_01' in self.task_name or 'Category3' in self.task_name or
                              'Category4' in self.task_name or 'Category5' in self.task_name or 'C_05' in self.task_name or
                              'F_01' in self.task_name or 'F_02' in self.task_name or 'F_03' in self.task_name or
                              'F_04' in self.task_name or 'F_05' in self.task_name or 'F_06' in self.task_name or
                              'Category6' in self.task_name or 'E_01' in self.task_name)
                if not skip_stuck and step_count > STABILIZATION_STEPS and last_position is not None:
                    dx = abs(current_pos[0] - last_position[0])
                    dy = abs(current_pos[1] - last_position[1])
                    # For walker tasks, use larger threshold since they move slowly
                    # Check if agent has forward velocity to avoid false stuck detection
                    has_forward_velocity = agent_body.linearVelocity.x > 0.01  # Very low threshold for slow walkers
                    # For walker tasks, use much larger position epsilon
                    walker_epsilon = POSITION_EPSILON * 5  # 5x larger threshold for walkers
                    if dx < walker_epsilon and dy < walker_epsilon and not has_forward_velocity:
                        stuck_counter += 1
                        # For walker tasks, use much longer stuck threshold
                        walker_stuck_threshold = STUCK_THRESHOLD * 5  # 5x longer for walkers (1500 steps)
                        if stuck_counter >= walker_stuck_threshold:
                            print(f"Detected Agent stuck, stopping simulation")
                            running = False
                            break
                    else:
                        stuck_counter = 0
                last_position = current_pos
                
                # Detect anomalies (K_05/K_06/D_01: skip - D_01 projectile can be fast and fall)
                skip_speed_check = ('K_05' in self.task_name or 'K_06' in self.task_name or 'D_01' in self.task_name or
                                   'Category3' in self.task_name or 'Category4' in self.task_name or 'F_02' in self.task_name or
                                   'Category5' in self.task_name or 'C_01' in self.task_name or
                                   'Category6' in self.task_name or 'E_01' in self.task_name)
                if not skip_speed_check:
                    speed = math.sqrt(agent_body.linearVelocity.x**2 + agent_body.linearVelocity.y**2)
                    if speed > 20:
                        print(f"Agent speed abnormal ({speed:.2f} m/s), stopping simulation")
                        running = False
                        break
                
                skip_fall_check = ('K_05' in self.task_name or 'K_06' in self.task_name or 'D_01' in self.task_name or
                                  'Category3' in self.task_name or 'Category4' in self.task_name or 'F_02' in self.task_name or
                                  'Category6' in self.task_name or 'E_01' in self.task_name)
                if not skip_fall_check and agent_body.position.y < -10:
                    print(f"Agent fell off map, stopping simulation")
                    running = False
                    break
            
            # Render
            if can_display and self.renderer and hasattr(self.renderer, 'render'):
                # Camera: D_06 fixed view so both ball (x=22) and catcher (x~10–12) are visible, no sway
                if 'D_06' in self.task_name:
                    fixed_center_x = 14.0  # world x for center of screen
                    target_x = fixed_center_x * self.simulator.ppm
                    camera_offset_x = target_x - self.simulator.screen_width / 2
                # Camera follow (K_04: follow object so we see pusher pushing from behind)
                elif 'K_04' in self.task_name and hasattr(self.environment, 'get_object_position'):
                    obj_pos = self.environment.get_object_position()
                    if obj_pos:
                        target_x = obj_pos[0] * self.simulator.ppm
                        camera_offset_x = target_x - self.simulator.screen_width / 2
                    elif agent_body:
                        target_x = agent_body.position.x * self.simulator.ppm
                        camera_offset_x = target_x - self.simulator.screen_width / 2
                    else:
                        camera_offset_x = 0
                elif ('Category6' in self.task_name or 'E_02' in self.task_name) and hasattr(self.environment, 'get_craft_position'):
                    craft_pos = self.environment.get_craft_position()
                    if craft_pos:
                        target_x = craft_pos[0] * self.simulator.ppm
                        camera_offset_x = target_x - self.simulator.screen_width / 2
                    else:
                        camera_offset_x = 0
                elif agent_body:
                    target_x = agent_body.position.x * self.simulator.ppm
                    camera_offset_x = target_x - self.simulator.screen_width / 2
                else:
                    camera_offset_x = 0
                
                # Get target (angle for control_aware, position for others)
                target_value = None
                if is_control_aware:
                    if self.evaluator and hasattr(self.evaluator, 'target_angle'):
                        target_value = self.evaluator.target_angle
                    elif self.evaluator and hasattr(self.evaluator, 'get_task_description'):
                        task_info = self.evaluator.get_task_description()
                        target_value = task_info.get('target_angle', 0)
                else:
                    if self.evaluator and hasattr(self.evaluator, 'target_x'):
                        target_value = self.evaluator.target_x
                    elif self.evaluator and hasattr(self.evaluator, 'get_task_description'):
                        task_info = self.evaluator.get_task_description()
                        target_value = task_info.get('target_position', 0)
                
                # Render
                try:
                    if is_control_aware:
                        self.renderer.render(self.environment, self.agent_components, target_value or 0, camera_offset_x)
                    else:
                        self.renderer.render(self.environment, agent_body, target_value or 0, camera_offset_x)
                except Exception as e:
                    print(f"Rendering error: {e}")
                
                # Refresh display
                self.simulator.flip()
                self.simulator.tick()
            
            # K_05: stop if object fell (physics exploded)
            if 'K_05' in self.task_name and hasattr(self.environment, 'get_object_position'):
                obj_pos = self.environment.get_object_position()
                if obj_pos and obj_pos[1] < -50:
                    print(f"K-05: Object fell (y={obj_pos[1]:.1f}), stopping simulation")
                    running = False
                    break
            # Collect frames (K_04/K_05/K_06: task-specific interval for visible motion in GIF)
            frame_interval = 50 if 'K_04' in self.task_name and save_gif else 10
            if 'K_05' in self.task_name and save_gif:
                frame_interval = 15  # enough frames to see "lift" (camera follows object Y)
            if 'K_06' in self.task_name and save_gif:
                frame_interval = 5   # dense frames so wiper sweep is visible
            if ('Category5' in self.task_name or 'C_05' in self.task_name) and save_gif:
                frame_interval = 3   # dense frames so A->B->C motion is visible
            self.simulator.collect_frame(step_count, frame_interval=frame_interval)
            
            # Evaluate (K_03 every 10; K_05 every step so 180 steps above target = 3s; others every 100)
            eval_interval = 10 if 'K_03' in self.task_name else (1 if 'K_05' in self.task_name else (1 if 'D_01' in self.task_name or 'Category3' in self.task_name or 'Category5' in self.task_name or 'C_01' in self.task_name else 100))
            do_eval = (step_count % eval_interval == 0 or (step_count == 1 and 'K_03' in self.task_name)) and self.evaluator
            if do_eval:
                if 'S_01' in self.task_name or 'Category1' in self.task_name:
                    # S_01 evaluator doesn't use agent_body
                    should_stop, score, metrics = self.evaluator.evaluate(
                        None, step_count, max_steps
                    )
                elif 'Category2' in self.task_name or 'K_01' in self.task_name or 'K_02' in self.task_name or 'K_03' in self.task_name or 'K_04' in self.task_name or 'K_05' in self.task_name or 'K_06' in self.task_name:
                    # Category2 tasks use agent_body
                    should_stop, score, metrics = self.evaluator.evaluate(
                        agent_body, step_count, max_steps
                    )
                elif 'Category3' in self.task_name or 'D_01' in self.task_name or 'D_02' in self.task_name or 'D_03' in self.task_name or 'D_04' in self.task_name or 'D_05' in self.task_name or 'D_06' in self.task_name:
                    # Category3 (Dynamics) tasks use agent_body
                    should_stop, score, metrics = self.evaluator.evaluate(
                        agent_body, step_count, max_steps
                    )
                elif 'Category4' in self.task_name or 'F_01' in self.task_name or 'F_02' in self.task_name or 'F_03' in self.task_name or 'F_04' in self.task_name or 'F_05' in self.task_name or 'F_06' in self.task_name:
                    # Category4 (Granular/Fluid) tasks use agent_body
                    should_stop, score, metrics = self.evaluator.evaluate(
                        agent_body, step_count, max_steps
                    )
                elif is_control_aware:
                    # ControlAware evaluator needs agent_components
                    should_stop, score, metrics = self.evaluator.evaluate(
                        self.agent_components, step_count, max_steps
                    )
                elif 'Category6' in self.task_name or 'E_02' in self.task_name:
                    # E_02 Thick Air: evaluator uses environment (craft position/heat), agent_body is None
                    should_stop, score, metrics = self.evaluator.evaluate(
                        None, step_count, max_steps
                    )
                elif agent_body:
                    should_stop, score, metrics = self.evaluator.evaluate(
                        agent_body, step_count, max_steps
                    )
                else:
                    should_stop, score, metrics = False, 0.0, {}
                
                # K_04: require min steps before early success stop (so GIF has enough frames)
                min_steps_for_early_stop = 2500 if 'K_04' in self.task_name else 0
                if should_stop and metrics.get('success') and step_count >= min_steps_for_early_stop:
                    print(f"\n🎉 Success! Agent completed task!")
                    running = False
                    break
                elif should_stop and metrics.get('success') and 'K_04' in self.task_name:
                    pass  # continue running to capture more GIF frames
                elif should_stop and metrics.get('failed'):
                    print(f"\n❌ Failed: {metrics.get('failure_reason', 'Unknown reason')}")
                    running = False
                    break
        
        # Final evaluation
        if self.evaluator:
            if 'S_01' in self.task_name or 'Category1' in self.task_name:
                # S_01 evaluator doesn't use agent_body
                final_should_stop, final_score, final_metrics = self.evaluator.evaluate(
                    None, step_count, max_steps
                )
            elif 'Category2' in self.task_name or 'K_01' in self.task_name or 'K_02' in self.task_name or 'K_03' in self.task_name or 'K_04' in self.task_name or 'K_05' in self.task_name or 'K_06' in self.task_name:
                # Category2 tasks use agent_body
                final_should_stop, final_score, final_metrics = self.evaluator.evaluate(
                    agent_body, step_count, max_steps
                )
            elif 'Category3' in self.task_name or 'D_01' in self.task_name or 'D_02' in self.task_name or 'D_03' in self.task_name or 'D_04' in self.task_name or 'D_05' in self.task_name or 'D_06' in self.task_name:
                # Category3 (Dynamics) tasks use agent_body
                final_should_stop, final_score, final_metrics = self.evaluator.evaluate(
                    agent_body, step_count, max_steps
                )
            elif 'Category4' in self.task_name or 'F_01' in self.task_name or 'F_02' in self.task_name or 'F_03' in self.task_name or 'F_04' in self.task_name or 'F_05' in self.task_name or 'F_06' in self.task_name:
                # Category4 (Granular/Fluid) tasks use agent_body
                final_should_stop, final_score, final_metrics = self.evaluator.evaluate(
                    agent_body, step_count, max_steps
                )
            elif is_control_aware:
                # ControlAware evaluator needs agent_components
                final_should_stop, final_score, final_metrics = self.evaluator.evaluate(
                    self.agent_components, step_count, max_steps
                )
            elif 'Category6' in self.task_name or 'E_02' in self.task_name:
                final_should_stop, final_score, final_metrics = self.evaluator.evaluate(
                    None, step_count, max_steps
                )
            elif agent_body:
                final_should_stop, final_score, final_metrics = self.evaluator.evaluate(
                    agent_body, step_count, max_steps
                )
            else:
                final_should_stop, final_score, final_metrics = False, 0.0, {}
            
            # Print results
            print(f"\n{'='*60}")
            print(f"Simulation ended, total steps: {step_count}")
            print(f"{'='*60}")
            print(f"\n📊 Evaluation Results:")
            if 'current_x' in final_metrics:
                print(f"  Final position: x={final_metrics['current_x']:.2f}m, y={final_metrics['current_y']:.2f}m")
            if 'craft_x' in final_metrics:
                print(f"  Craft position: x={final_metrics['craft_x']:.2f}m, y={final_metrics['craft_y']:.2f}m")
            if 'heat' in final_metrics:
                print(f"  Heat: {final_metrics['heat']:.1f} N·s (limit: {final_metrics.get('overheat_limit', 5000):.0f})")
            if 'target_x' in final_metrics:
                print(f"  Target position: x={final_metrics['target_x']:.2f}m")
            if 'distance_traveled' in final_metrics:
                print(f"  Distance traveled: {final_metrics['distance_traveled']:.2f}m")
            if 'progress' in final_metrics:
                print(f"  Completion progress: {final_metrics['progress']:.1f}%")
            print(f"  Final score: {final_score:.1f}/100")
            if final_metrics.get('success'):
                print(f"  ✅ Task successful!")
            elif final_metrics.get('failed'):
                print(f"  ❌ Task failed: {final_metrics.get('failure_reason', 'Unknown reason')}")
            else:
                print(f"  ⚠️  Task not completed")
            print(f"{'='*60}\n")
            
            # Save GIF
            if save_gif:
                # For Category1 and Category2 tasks, save to task directory
                if 'Category1' in self.task_name or 'S_01' in self.task_name or 'S_02' in self.task_name or 'S_03' in self.task_name or 'S_04' in self.task_name or 'S_05' in self.task_name or 'S_06' in self.task_name:
                    # Extract task name (e.g., "Category1_Statics_Equilibrium.S_01" -> "S_01")
                    task_parts = self.task_name.split('.')
                    if len(task_parts) > 1:
                        short_task_name = task_parts[-1]
                        category = task_parts[0]
                        task_dir = os.path.join(os.path.dirname(__file__), 'tasks', category, short_task_name)
                        os.makedirs(task_dir, exist_ok=True)
                        gif_filename = os.path.join(task_dir, 'reference_solution_success.gif')
                elif 'Category2' in self.task_name or 'K_01' in self.task_name or 'K_02' in self.task_name or 'K_03' in self.task_name or 'K_04' in self.task_name or 'K_05' in self.task_name or 'K_06' in self.task_name:
                    # For Category2 tasks, save to task directory (absolute path so IDE/editor sees update)
                    task_parts = self.task_name.split('.')
                    if len(task_parts) > 1:
                        short_task_name = task_parts[-1]
                        category = task_parts[0]
                        task_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'tasks', category, short_task_name))
                        os.makedirs(task_dir, exist_ok=True)
                        gif_filename = os.path.join(task_dir, 'solution_success.gif')
                    else:
                        gif_dir = "../gif"
                        gif_filename = os.path.join(gif_dir, f"{self.task_name}_animation.gif")
                elif 'Category3' in self.task_name or 'D_01' in self.task_name or 'D_02' in self.task_name or 'D_03' in self.task_name or 'D_04' in self.task_name or 'D_05' in self.task_name or 'D_06' in self.task_name:
                    # For Category3 (Dynamics) tasks, save to task directory; only overwrite success GIF when actually successful
                    task_parts = self.task_name.split('.')
                    if len(task_parts) > 1:
                        short_task_name = task_parts[-1]
                        category = task_parts[0]
                        task_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'tasks', category, short_task_name))
                        os.makedirs(task_dir, exist_ok=True)
                        if final_metrics.get('success'):
                            gif_filename = os.path.join(task_dir, 'reference_solution_success.gif')
                        else:
                            gif_filename = os.path.join(task_dir, 'reference_solution_failure.gif')
                    else:
                        gif_dir = "../gif"
                        gif_filename = os.path.join(gif_dir, f"{self.task_name}_animation.gif")
                elif 'Category4' in self.task_name or 'F_01' in self.task_name or 'F_02' in self.task_name or 'F_03' in self.task_name or 'F_04' in self.task_name or 'F_05' in self.task_name or 'F_06' in self.task_name:
                    # For Category4 (Granular/Fluid) tasks, save to task directory
                    task_parts = self.task_name.split('.')
                    if len(task_parts) > 1:
                        short_task_name = task_parts[-1]
                        category = task_parts[0]
                        task_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'tasks', category, short_task_name))
                        os.makedirs(task_dir, exist_ok=True)
                        if final_metrics.get('success'):
                            gif_filename = os.path.join(task_dir, 'reference_solution_success.gif')
                        else:
                            gif_filename = os.path.join(task_dir, 'reference_solution_failure.gif')
                    else:
                        gif_dir = "../gif"
                        gif_filename = os.path.join(gif_dir, f"{self.task_name}_animation.gif")
                elif 'Category5' in self.task_name or 'C_05' in self.task_name:
                    # For Category5 (Cybernetics/Control) e.g. C_05 Logic Lock
                    task_parts = self.task_name.split('.')
                    if len(task_parts) > 1:
                        short_task_name = task_parts[-1]
                        category = task_parts[0]
                        task_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'tasks', category, short_task_name))
                        os.makedirs(task_dir, exist_ok=True)
                        if final_metrics.get('success'):
                            gif_filename = os.path.join(task_dir, 'reference_solution_success.gif')
                        else:
                            gif_filename = os.path.join(task_dir, 'reference_solution_failure.gif')
                    else:
                        gif_dir = "../gif"
                        gif_filename = os.path.join(gif_dir, f"{self.task_name}_animation.gif")
                elif 'Category6' in self.task_name or 'E_02' in self.task_name:
                    task_parts = self.task_name.split('.')
                    if len(task_parts) > 1:
                        short_task_name = task_parts[-1]
                        category = task_parts[0]
                        task_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'tasks', category, short_task_name))
                        os.makedirs(task_dir, exist_ok=True)
                        if final_metrics.get('success'):
                            gif_filename = os.path.join(task_dir, 'reference_solution_success.gif')
                        else:
                            gif_filename = os.path.join(task_dir, 'reference_solution_failure.gif')
                    else:
                        gif_dir = "../gif"
                        gif_filename = os.path.join(gif_dir, f"{self.task_name}_animation.gif")
                elif 'demo' in self.task_name:
                    # For demo tasks, save to task directory
                    task_parts = self.task_name.split('.')
                    if len(task_parts) > 1:
                        category = task_parts[0]  # e.g., "demo"
                        task_name = task_parts[1]  # e.g., "control_aware"
                        task_dir = os.path.join(os.path.dirname(__file__), 'tasks', category, task_name)
                        os.makedirs(task_dir, exist_ok=True)
                        gif_filename = os.path.join(task_dir, f'{task_name}_success.gif')
                    else:
                        gif_dir = "../gif"
                        gif_filename = os.path.join(gif_dir, f"{self.task_name}_animation.gif")
                elif 'Category6' in self.task_name or 'E_01' in self.task_name or 'E_02' in self.task_name:
                    # Category 6 (Exotic Physics) e.g. E_01 Inverted Gravity
                    task_parts = self.task_name.split('.')
                    if len(task_parts) > 1:
                        short_task_name = task_parts[-1]
                        category = task_parts[0]
                        task_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'tasks', category, short_task_name))
                        os.makedirs(task_dir, exist_ok=True)
                        if final_metrics.get('success'):
                            gif_filename = os.path.join(task_dir, 'reference_solution_success.gif')
                        else:
                            gif_filename = os.path.join(task_dir, 'reference_solution_failure.gif')
                    else:
                        gif_dir = "../gif"
                        gif_filename = os.path.join(gif_dir, f"{self.task_name}_animation.gif")
                else:
                    gif_dir = "../gif"
                    gif_filename = os.path.join(gif_dir, f"{self.task_name}_animation.gif")
                self.simulator.save_gif_animation(gif_filename)
                if 'Category3' in self.task_name or 'D_06' in self.task_name:
                    print(f"\nGIF saved: {gif_filename}")
            
            return final_score, final_metrics
        
        return None, {}
    
    def _run_classify_balls_loop(self, max_steps, can_display, save_gif):
        """Run ClassifyBalls task simulation loop"""
        step_count = 0
        running = True
        camera_offset_x = 0
        
        while running and step_count < max_steps:
            # Handle events
            if not self.simulator.handle_events():
                running = False
                break
            
            # Spawn balls
            if self.environment.balls_spawned < self.environment.balls_to_spawn:
                self.environment.ball_spawn_timer += 1
                # Use base interval, can add random variation
                spawn_interval = self.environment.ball_spawn_interval_base
                if self.environment.ball_spawn_timer >= spawn_interval:
                    color = self.environment.ball_spawn_order[self.environment.balls_spawned]
                    ball = self.environment.spawn_ball(color)
                    if ball:
                        print(f"Spawned {color} ball #{self.environment.balls_spawned}")
                    self.environment.ball_spawn_timer = 0
            
            # Agent executes action
            if hasattr(self.task_module.agent, 'agent_action'):
                self.task_module.agent.agent_action(
                    self.environment, self.agent_components, step_count
                )
            
            # Physics step
            self.environment.step(TIME_STEP)
            step_count += 1
            
            # Render (use task-specific renderer)
            if can_display and self.renderer and hasattr(self.renderer, 'render'):
                # Camera fixed at conveyor center, don't follow balls
                target_x = (self.environment.conveyor_start_x + self.environment.conveyor_end_x) / 2 * self.simulator.ppm
                camera_offset_x = target_x - self.simulator.screen_width / 2
                
                # Use task-specific renderer
                try:
                    self.renderer.render(self.environment, self.agent_components, camera_offset_x)
                except Exception as e:
                    print(f"Rendering error: {e}")
                    import traceback
                    traceback.print_exc()
                
                self.simulator.flip()
                self.simulator.tick()
            
            # Collect frames
            self.simulator.collect_frame(step_count)
            
            # Evaluate
            if step_count % 100 == 0 and self.evaluator:
                should_stop, score, metrics = self.evaluator.evaluate(step_count, max_steps)
                
                if should_stop and metrics.get('success'):
                    print(f"\n🎉 Success! All balls correctly classified!")
                    running = False
                    break
                elif should_stop:
                    print(f"\n⏹️  Simulation ended (all balls spawned and classified)")
                    running = False
                    break
        
        # Final evaluation
        if self.evaluator:
            final_should_stop, final_score, final_metrics = self.evaluator.evaluate(step_count, max_steps)
            
            print(f"\n{'='*60}")
            print(f"Simulation ended, total steps: {step_count}")
            print(f"{'='*60}")
            print(f"\n📊 Evaluation Results:")
            print(f"  Total balls: {final_metrics.get('total_balls', 0)}")
            print(f"  Classification accuracy: {final_metrics.get('accuracy', 0):.1f}%")
            print(f"  Final score: {final_score:.1f}/100")
            if final_metrics.get('success'):
                print(f"  ✅ Task successful!")
            elif final_score >= 100.0:
                print(f"  ✅ Task successful! (100% accuracy)")
            else:
                print(f"  ⚠️  Task not fully successful")
            print(f"{'='*60}\n")
            
            # Save GIF
            if save_gif:
                # Save GIF to task directory
                task_dir = os.path.join(os.path.dirname(__file__), 'tasks', 'demo', 'classify_balls')
                os.makedirs(task_dir, exist_ok=True)
                gif_filename = os.path.join(task_dir, "classify_balls_optimized_success.gif")
                self.simulator.save_gif_animation(gif_filename)
            
            return final_score, final_metrics
        
        return None, {}


# Alias short task names to full module paths (category_N_MM -> CategoryN_... .F_MM / etc.)
TASK_ALIASES = {
    'category_1_01': 'Category1_Statics_Equilibrium.S_01',
    'category_1_02': 'Category1_Statics_Equilibrium.S_02',
    'category_1_03': 'Category1_Statics_Equilibrium.S_03',
    'category_1_04': 'Category1_Statics_Equilibrium.S_04',
    'category_1_05': 'Category1_Statics_Equilibrium.S_05',
    'category_1_06': 'Category1_Statics_Equilibrium.S_06',
    'category_2_01': 'Category2_Kinematics_Linkages.K_01',
    'category_2_02': 'Category2_Kinematics_Linkages.K_02',
    'category_2_03': 'Category2_Kinematics_Linkages.K_03',
    'category_2_04': 'Category2_Kinematics_Linkages.K_04',
    'category_2_05': 'Category2_Kinematics_Linkages.K_05',
    'category_2_06': 'Category2_Kinematics_Linkages.K_06',
    'category_3_01': 'Category3_Dynamics_Energy.D_01',
    'category_3_02': 'Category3_Dynamics_Energy.D_02',
    'category_3_03': 'Category3_Dynamics_Energy.D_03',
    'category_3_04': 'Category3_Dynamics_Energy.D_04',
    'category_3_05': 'Category3_Dynamics_Energy.D_05',
    'category_3_06': 'Category3_Dynamics_Energy.D_06',
    'category_4_01': 'Category4_Granular_FluidInteraction.F_01',
    'category_4_02': 'Category4_Granular_FluidInteraction.F_02',
    'category_4_03': 'Category4_Granular_FluidInteraction.F_03',
    'category_4_04': 'Category4_Granular_FluidInteraction.F_04',
    'category_4_05': 'Category4_Granular_FluidInteraction.F_05',
    'category_4_06': 'Category4_Granular_FluidInteraction.F_06',
    'category_5_01': 'Category5_Cybernetics_Control.C_01',
    'category_5_02': 'Category5_Cybernetics_Control.C_02',
    'category_5_03': 'Category5_Cybernetics_Control.C_03',
    'category_5_04': 'Category5_Cybernetics_Control.C_04',
    'category_5_05': 'Category5_Cybernetics_Control.C_05',
    'category_5_06': 'Category5_Cybernetics_Control.C_06',
    'category_6_01': 'Category6_ExoticPhysics.E_01',
    'category_6_02': 'Category6_ExoticPhysics.E_02',
    'category_6_03': 'Category6_ExoticPhysics.E_03',
    'category_6_04': 'Category6_ExoticPhysics.E_04',
    'category_6_05': 'Category6_ExoticPhysics.E_05',
    'category_6_06': 'Category6_ExoticPhysics.E_06'
}


def run_task(task_name, headless=False, max_steps=None, save_gif=False, env_overrides=None):
    """
    Run specified task
    Args:
        task_name: Task name (e.g. 'basic', 'classify_balls', 'simple_task', 'category_4_01', 'category_5_01', 'category_6_01', 'category_6_02', 'category_6_03', 'category_6_04', 'category_6_05', 'category_6_06')
        headless: Whether headless mode
        max_steps: Maximum steps
        save_gif: Whether to save GIF
        env_overrides: Optional dict with terrain_config and/or physics_config for the environment
    """
    # Resolve alias to full module path
    task_name = TASK_ALIASES.get(task_name, task_name)
    # Dynamically import task module
    try:
        task_module = __import__(f'tasks.{task_name}', fromlist=['environment', 'evaluator', 'agent', 'renderer'])
    except ImportError as e:
        print(f"Cannot import task module '{task_name}': {e}")
        print(f"Available tasks: basic, classify_balls, simple_task, category_4_01, category_5_01, category_6_01, category_6_02, category_6_03, category_6_04, category_6_05, category_6_06")
        return None
    
    # Create and run task
    runner = TaskRunner(task_name, task_module)
    return runner.run(headless=headless, max_steps=max_steps, save_gif=save_gif, env_overrides=env_overrides)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='DaVinciBench top-level script')
    parser.add_argument('--task', type=str, default='basic',
                       choices=['basic', 'classify_balls', 'simple_task', 'category_4_01', 'category_5_01', 'category_6_01', 'category_6_02', 'category_6_03', 'category_6_04', 'category_6_05', 'category_6_06', 'category_4_02', 'category_4_03', 'category_4_04', 'category_4_05', 'category_4_06', 'category_5_02', 'category_5_03', 'category_5_04', 'category_5_05', 'category_5_06', 'category_1_01', 'category_1_02', 'category_1_03', 'category_1_04', 'category_1_05', 'category_1_06', 'category_2_01', 'category_2_02', 'category_2_03', 'category_2_04', 'category_2_05', 'category_2_06', 'category_3_01', 'category_3_02', 'category_3_03', 'category_3_04', 'category_3_05', 'category_3_06'],
                       help='Task to run')
    parser.add_argument('--headless', action='store_true',
                       help='Headless mode (no window display)')
    parser.add_argument('--steps', type=int, default=None,
                       help='Maximum steps')
    parser.add_argument('--gif', '--animation', action='store_true',
                       help='Save GIF animation')
    parser.add_argument('--display', '--gui', action='store_true',
                       help='Force enable graphics display')
    
    args = parser.parse_args()
    
    # If GIF saving enabled, create offscreen surface even in headless mode
    if args.gif:
        args.headless = False
    
    # Run task
    run_task(args.task, headless=args.headless, max_steps=args.steps, save_gif=args.gif)
