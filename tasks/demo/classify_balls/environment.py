"""
ClassifyBalls task environment module
New design: Conveyor on left, Agent in middle build area, bins below
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, 
                      revoluteJoint, prismaticJoint, weldJoint)
import math
import random


class BallClassificationSandbox:
    """Ball classification task environment"""
    
    def __init__(self, terrain_config=None, physics_config=None):
        # 1. Initialize physics world
        self.world = world(gravity=(0, -9.8), doSleep=True)
        self.bodies = []
        self.joints = []
        self.sensors = []  # Sensor list
        self.actuators = []  # Actuator list (pistons, motors, etc.)
        self.logic_gates = []  # Logic gate list
        self.wires = []  # Wire list
        self.balls = []  # Ball list
        
        # 2. Environment geometry parameters
        # Conveyor: From (-5, 5) to (0, 5), length 5m
        CONVEYOR_START_X = -5.0
        CONVEYOR_END_X = 0.0
        CONVEYOR_Y = 5.0
        CONVEYOR_LENGTH = 5.0
        CONVEYOR_WIDTH = 0.3
        
        # Create conveyor
        self.conveyor = self.world.CreateStaticBody(
            position=((CONVEYOR_START_X + CONVEYOR_END_X) / 2, CONVEYOR_Y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(CONVEYOR_LENGTH/2, CONVEYOR_WIDTH/2)),
                friction=0.8,  # High friction, ensure balls don't slip
                restitution=0.0
            )
        )
        self.conveyor_speed = 2.0  # Faster speed - balls move more quickly
        self.conveyor_start_x = CONVEYOR_START_X
        self.conveyor_end_x = CONVEYOR_END_X
        self.conveyor_y = CONVEYOR_Y
        
        # 3. Spawn point: (-4, 6)
        self.spawn_point = (-4.0, 6.0)
        
        # 4. Agent build area: (0.5, 0) to (5, 5)
        self.build_zone = {
            'min_x': 0.5,
            'max_x': 5.0,
            'min_y': 0.0,
            'max_y': 5.0
        }
        
        # 5. Target bins
        # Separated bins: Blue on left, Red on right - NO OVERLAP
        # Blue bin (Bin A): Left side, for balls that naturally fall
        # Made wider and positioned to catch naturally falling balls
        self.blue_basket = {
            'x': 0.5,  # Closer to conveyor end
            'y': 0.0,
            'width': 3.5,  # Wider - covers from -1.25 to 2.25
            'height': 4.0,
            'color': 'blue'
        }
        
        # Red bin (Bin B): Right side, for balls pushed rightward
        # Positioned further right to ensure clear separation
        self.red_basket = {
            'x': 4.0,  # Further right for clear separation
            'y': 0.0,
            'width': 3.0,  # Wider - covers from 2.5 to 5.5
            'height': 4.0,
            'color': 'red'
        }
        
        # Create bin boundaries (open boxes)
        basket_wall_height = 0.2
        # Blue bin
        self.world.CreateStaticBody(
            position=(self.blue_basket['x'] - self.blue_basket['width']/2, 
                     self.blue_basket['y'] + basket_wall_height/2),
            shapes=polygonShape(box=(0.05, basket_wall_height/2))
        )
        self.world.CreateStaticBody(
            position=(self.blue_basket['x'] + self.blue_basket['width']/2, 
                     self.blue_basket['y'] + basket_wall_height/2),
            shapes=polygonShape(box=(0.05, basket_wall_height/2))
        )
        # Red bin
        self.world.CreateStaticBody(
            position=(self.red_basket['x'] - self.red_basket['width']/2, 
                     self.red_basket['y'] + basket_wall_height/2),
            shapes=polygonShape(box=(0.05, basket_wall_height/2))
        )
        self.world.CreateStaticBody(
            position=(self.red_basket['x'] + self.red_basket['width']/2, 
                     self.red_basket['y'] + basket_wall_height/2),
            shapes=polygonShape(box=(0.05, basket_wall_height/2))
        )
        
        # 6. Ball spawn parameters
        # Extremely simplified: Maximum time between spawns, minimum balls
        self.ball_radius = 0.3
        self.ball_spawn_timer = 0
        self.ball_spawn_interval_base = 900  # 15 seconds (60fps * 15) - more time between balls
        self.balls_to_spawn = 4  # Keep at 4
        self.balls_spawned = 0
        # Fixed order: red, blue alternating (easier for consistent behavior)
        self.ball_spawn_order = ['red', 'blue'] * 2  # 4 balls total
        # Removed random.shuffle for consistent testing
        
        # 7. Ground (below bins)
        self.ground = self.world.CreateStaticBody(
            position=(0, -1),
            shapes=polygonShape(box=(20, 0.5))
        )
    
    # --- Physical constraint constants ---
    MAX_BEAM_LENGTH = 5.0
    MIN_BEAM_LENGTH = 0.1
    MAX_PLATE_SIZE = 2.0
    MAX_PISTON_LENGTH = 5.0  # Increased for longer reach
    MAX_MOTOR_TORQUE = 3000.0  # Further increased for maximum power
    SENSOR_MAX_LENGTH = 5.0
    
    # --- Primitives API ---
    
    def add_beam(self, start_pos, end_pos, material='steel', density=1.0):
        """
        Add rigid beam
        Args:
            start_pos: (x, y) Start position
            end_pos: (x, y) End position
            material: Material type (affects density)
            density: Density
        """
        # Check if within build area
        if not (self.build_zone['min_x'] <= start_pos[0] <= self.build_zone['max_x'] and
                self.build_zone['min_y'] <= start_pos[1] <= self.build_zone['max_y']):
            raise ValueError(f"Start position {start_pos} not in build area")
        if not (self.build_zone['min_x'] <= end_pos[0] <= self.build_zone['max_x'] and
                self.build_zone['min_y'] <= end_pos[1] <= self.build_zone['max_y']):
            raise ValueError(f"End position {end_pos} not in build area")
        
        length = math.sqrt((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)
        if length < self.MIN_BEAM_LENGTH or length > self.MAX_BEAM_LENGTH:
            raise ValueError(f"Beam length {length} out of range [{self.MIN_BEAM_LENGTH}, {self.MAX_BEAM_LENGTH}]")
        
        # Calculate center point and angle
        center_x = (start_pos[0] + end_pos[0]) / 2
        center_y = (start_pos[1] + end_pos[1]) / 2
        angle = math.atan2(end_pos[1] - start_pos[1], end_pos[0] - start_pos[0])
        
        # Create thin rectangle as beam
        beam_width = 0.05
        body = self.world.CreateDynamicBody(
            position=(center_x, center_y),
            angle=angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(length/2, beam_width/2)),
                density=density,
                friction=0.5,
            )
        )
        self.bodies.append(body)
        return body
    
    def add_plate(self, center, width, height, angle=0, density=1.0):
        """
        Add plate
        Args:
            center: (x, y) Center position
            width: Width
            height: Height
            angle: Angle (radians)
            density: Density
        """
        if not (self.build_zone['min_x'] <= center[0] <= self.build_zone['max_x'] and
                self.build_zone['min_y'] <= center[1] <= self.build_zone['max_y']):
            raise ValueError(f"Center position {center} not in build area")
        
        if width > self.MAX_PLATE_SIZE or height > self.MAX_PLATE_SIZE:
            raise ValueError(f"Plate size exceeds maximum limit {self.MAX_PLATE_SIZE}")
        
        body = self.world.CreateDynamicBody(
            position=center,
            angle=angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(width/2, height/2)),
                density=density,
                friction=0.3,
            )
        )
        self.bodies.append(body)
        return body
    
    def add_joint(self, body_a, body_b, anchor_point, joint_type='revolute'):
        """
        Add joint
        Args:
            body_a: First body
            body_b: Second body
            anchor_point: (x, y) Anchor point position
            joint_type: 'revolute' (rotating) or 'fixed' (fixed)
        """
        if joint_type == 'revolute':
            joint = self.world.CreateRevoluteJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=anchor_point,
                collideConnected=False
            )
        else:  # fixed - use weld joint
            try:
                joint = self.world.CreateWeldJoint(
                    bodyA=body_a,
                    bodyB=body_b,
                    anchor=anchor_point
                )
            except:
                # If weld joint not available, use revolute joint and limit angle
                joint = self.world.CreateRevoluteJoint(
                    bodyA=body_a,
                    bodyB=body_b,
                    anchor=anchor_point,
                    enableLimit=True,
                    lowerAngle=0.0,
                    upperAngle=0.0,
                    collideConnected=False
                )
        self.joints.append(joint)
        return joint
    
    def add_piston(self, base_pos, direction, max_length, speed, density=1.0):
        """
        Add piston/pusher
        Args:
            base_pos: (x, y) Base position
            direction: (dx, dy) Direction vector (normalized)
            max_length: Maximum extension length
            speed: Speed (m/s)
            density: Density
        """
        # Allow piston near conveyor end (x can be slightly less than 0.5, but within reasonable range)
        # Ensure piston rod extension is within or near build area
        min_x_allowed = -0.5  # Allow slightly outside build area, but near conveyor
        if not (min_x_allowed <= base_pos[0] <= self.build_zone['max_x'] and
                self.build_zone['min_y'] <= base_pos[1] <= self.build_zone['max_y']):
            raise ValueError(f"Base position {base_pos} not in allowed build area (allow x>={min_x_allowed})")
        
        if max_length > self.MAX_PISTON_LENGTH:
            raise ValueError(f"Piston maximum length {max_length} exceeds limit {self.MAX_PISTON_LENGTH}")
        
        # Normalize direction
        dir_len = math.sqrt(direction[0]**2 + direction[1]**2)
        if dir_len < 0.01:
            raise ValueError("Direction vector cannot be zero")
        direction = (direction[0] / dir_len, direction[1] / dir_len)
        
        # Create piston rod (thin rectangle)
        # FIXED: Piston should start in RETRACTED state, not extended!
        # The rod is a small "push head" that moves along the direction
        # Increased size for better collision detection and pushing force
        piston_width = 0.15  # Wider for better contact
        piston_head_length = 0.5  # Longer push head for better contact
        
        # Initial position: at base position (retracted state)
        piston_center = (base_pos[0] + direction[0] * piston_head_length/2,
                        base_pos[1] + direction[1] * piston_head_length/2)
        piston_angle = math.atan2(direction[1], direction[0])
        
        piston_body = self.world.CreateDynamicBody(
            position=piston_center,
            angle=piston_angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(piston_head_length/2, piston_width/2)),
                density=density,
                friction=0.3,  # Lower friction for smoother pushing
                restitution=0.1  # Slight bounce for better contact
            )
        )
        
        # Create base (fixed)
        base_body = self.world.CreateStaticBody(position=base_pos)
        
        # Create prismatic joint
        joint = self.world.CreatePrismaticJoint(
            bodyA=base_body,
            bodyB=piston_body,
            anchor=base_pos,
            axis=direction,
            lowerTranslation=0.0,
            upperTranslation=max_length,
            enableLimit=True,
            maxMotorForce=10000.0,  # Much higher force to ensure piston can push ball reliably
            motorSpeed=0.0,
            enableMotor=True
        )
        
        piston = {
            'body': piston_body,
            'base': base_body,
            'joint': joint,
            'direction': direction,
            'max_length': max_length,
            'speed': speed,
            'current_length': 0.0,
            'target_length': 0.0,
            'active': False
        }
        self.actuators.append(piston)
        self.bodies.append(piston_body)
        self.joints.append(joint)
        return piston
    
    def activate_piston(self, piston, activate=True):
        """Activate/deactivate piston"""
        piston['active'] = activate
        if activate:
            piston['target_length'] = piston['max_length']
            # Set motor speed to extend piston
            piston['joint'].motorSpeed = piston['speed']
            # Ensure motor enabled
            if hasattr(piston['joint'], 'enableMotor'):
                piston['joint'].enableMotor = True
        else:
            piston['target_length'] = 0.0
            # Set motor speed to retract piston
            piston['joint'].motorSpeed = -piston['speed']
            # Ensure motor enabled (for retraction)
            if hasattr(piston['joint'], 'enableMotor'):
                piston['joint'].enableMotor = True
        
        # Update current length (for subsequent checks)
        try:
            if hasattr(piston['joint'], 'GetJointTranslation'):
                piston['current_length'] = piston['joint'].GetJointTranslation()
            else:
                # Estimate length
                pos_diff = (piston['body'].position.x - piston['base'].position.x,
                           piston['body'].position.y - piston['base'].position.y)
                piston['current_length'] = math.sqrt(pos_diff[0]**2 + pos_diff[1]**2)
        except:
            piston['current_length'] = 0.0
    
    def add_motor(self, body, anchor_point, torque, speed):
        """
        Add motor
        Args:
            body: Body to drive
            anchor_point: (x, y) Anchor point
            torque: Torque
            speed: Angular velocity (rad/s)
        """
        if torque > self.MAX_MOTOR_TORQUE:
            raise ValueError(f"Torque {torque} exceeds maximum limit {self.MAX_MOTOR_TORQUE}")
        
        # Create fixed base
        base_body = self.world.CreateStaticBody(position=anchor_point)
        
        # Create revolute joint
        joint = self.world.CreateRevoluteJoint(
            bodyA=base_body,
            bodyB=body,
            anchor=anchor_point,
            enableMotor=True,
            maxMotorTorque=torque,
            motorSpeed=0.0  # Initial speed 0
        )
        
        motor = {
            'body': body,
            'joint': joint,
            'torque': torque,
            'target_speed': 0.0,
            'current_speed': speed
        }
        self.actuators.append(motor)
        self.joints.append(joint)
        return motor
    
    def set_motor_speed(self, motor, speed):
        """Set motor speed"""
        motor['target_speed'] = speed
        motor['joint'].motorSpeed = speed
    
    def add_raycast_sensor(self, origin, direction, length):
        """
        Add raycast sensor
        Args:
            origin: (x, y) Origin point
            direction: (dx, dy) Direction vector (normalized)
            length: Ray length
        """
        if length > self.SENSOR_MAX_LENGTH:
            raise ValueError(f"Sensor length {length} exceeds maximum limit {self.SENSOR_MAX_LENGTH}")
        
        # Normalize direction
        dir_len = math.sqrt(direction[0]**2 + direction[1]**2)
        if dir_len < 0.01:
            raise ValueError("Direction vector cannot be zero")
        direction = (direction[0] / dir_len, direction[1] / dir_len)
        
        sensor = {
            'origin': origin,
            'direction': direction,
            'length': length,
            'detected_object': None,
            'detected_color': 'NONE',
            'last_raycast_result': None
        }
        self.sensors.append(sensor)
        return sensor
    
    def get_detected_object_color(self, sensor):
        """Get detected object color from sensor"""
        return sensor['detected_color']
    
    def add_logic_and(self, input_a, input_b):
        """Logic AND gate"""
        gate = {
            'type': 'AND',
            'input_a': input_a,
            'input_b': input_b,
            'output': False
        }
        self.logic_gates.append(gate)
        return gate
    
    def add_logic_or(self, input_a, input_b):
        """Logic OR gate"""
        gate = {
            'type': 'OR',
            'input_a': input_a,
            'input_b': input_b,
            'output': False
        }
        self.logic_gates.append(gate)
        return gate
    
    def add_logic_not(self, input_a):
        """Logic NOT gate"""
        gate = {
            'type': 'NOT',
            'input_a': input_a,
            'output': False
        }
        self.logic_gates.append(gate)
        return gate
    
    def add_delay(self, input_signal, delay_seconds, output_duration=0.1):
        """
        Add delay
        Args:
            input_signal: Input signal (can be sensor, logic gate, etc.)
            delay_seconds: Delay seconds
            output_duration: Output duration (seconds), default 0.1s
        """
        delay = {
            'type': 'DELAY',
            'input': input_signal,
            'delay': delay_seconds,
            'output_duration': output_duration,
            'buffer': [],  # Store historical signals
            'output': False,
            'last_input': False
        }
        self.logic_gates.append(delay)
        return delay
    
    def add_wire(self, source, target):
        """
        Add wire
        Args:
            source: Source (sensor, logic gate, etc.)
            target: Target (actuator, logic gate, etc.)
        """
        wire = {
            'source': source,
            'target': target
        }
        self.wires.append(wire)
        return wire
    
    def spawn_ball(self, color):
        """Spawn a ball at spawn point"""
        if self.balls_spawned >= self.balls_to_spawn:
            return None
        
        spawn_x, spawn_y = self.spawn_point
        
        # Ensure ball spawns on conveyor top surface
        # Conveyor at y=5.0, width 0.3, top surface at y=5.15
        CONVEYOR_TOP_Y = self.conveyor_y + 0.15
        # 【修改点 3】温柔放置：稍微给一点点微米级的悬空，避免碰撞体积重叠被弹开
        spawn_y = CONVEYOR_TOP_Y + self.ball_radius + 0.001
        
        # Create ball
        # Simplified: Very light balls with high horizontal velocity for easier classification
        ball_body = self.world.CreateDynamicBody(
            position=(spawn_x, spawn_y),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=self.ball_radius),
                density=0.5,  # Ultra light - extremely easy to push
                friction=0.0,  # No friction, prevent rotation
                restitution=0.2  # More bounce for better interaction with deflectors
            )
        )
        
        # Give ball initial velocity (rightward, simulate conveyor speed)
        # Higher speed means balls travel further right naturally
        ball_body.linearVelocity = (self.conveyor_speed * 1.5, 0.0)  # Extra boost for easier pushing
        
        # Store ball metadata
        ball_data = {
            'body': ball_body,
            'color': color,
            'classified': False,
            'in_basket': False
        }
        self.balls.append(ball_data)
        self.balls_spawned += 1
        
        return ball_body
    
    def step(self, time_step):
        """Physics step - OPTIMIZED FOR DETERMINISM"""
        # Update ball velocities on conveyor
        CONVEYOR_TOP_Y = self.conveyor_y + 0.15
        for ball_data in self.balls:
            ball = ball_data['body']
            ball_x = ball.position.x
            ball_y = ball.position.y
            
            # If ball is on conveyor
            if (self.conveyor_start_x <= ball_x <= self.conveyor_end_x and
                ball_y >= CONVEYOR_TOP_Y and ball_y <= CONVEYOR_TOP_Y + 1.0):
                # 【修改点 1】上帝模式：强制锁定速度
                # 不再使用 ApplyForce，直接覆盖 velocity
                # 消除所有摩擦力、弹跳带来的微小误差
                ball.linearVelocity = (self.conveyor_speed * 1.2, 0.0)  # Slightly faster on conveyor
                ball.angularVelocity = 0.0  # 禁止旋转，防止球带旋飞出
                
                # 【修改点 2】强制吸附：防止球在传送带上微小弹跳
                # 强行把球按在传送带表面
                if ball_y > CONVEYOR_TOP_Y + self.ball_radius + 0.01:
                    ball.position = (ball_x, CONVEYOR_TOP_Y + self.ball_radius)
        
        # Physics step (execute first, then update sensors and logic)
        self.world.Step(time_step, 10, 10)
        
        # Execute raycast detection (update sensors)
        for sensor in self.sensors:
            self._update_sensor(sensor)
        
        # Update logic gates
        self._update_logic_gates(time_step)
        
        # Update actuators (based on logic gate output)
        self._update_actuators()
    
    def _update_sensor(self, sensor):
        """Update sensor (execute raycast detection)"""
        origin = sensor['origin']
        direction = sensor['direction']
        length = sensor['length']
        
        # Calculate end point
        end_point = (origin[0] + direction[0] * length,
                    origin[1] + direction[1] * length)
        
        # Simplified raycast detection: Check if any balls are near ray path
        # Calculate shortest distance from ray to ball
        min_distance = float('inf')
        closest_ball = None
        
        for ball_data in self.balls:
            ball = ball_data['body']
            ball_pos = ball.position
            
            # Calculate distance from point to line segment
            # Line segment: from origin to end_point
            # Point: ball_pos
            dx = end_point[0] - origin[0]
            dy = end_point[1] - origin[1]
            if dx == 0 and dy == 0:
                continue
            
            # Calculate projection point
            t = max(0, min(1, ((ball_pos.x - origin[0]) * dx + (ball_pos.y - origin[1]) * dy) / (dx*dx + dy*dy)))
            proj_x = origin[0] + t * dx
            proj_y = origin[1] + t * dy
            
            # Calculate distance
            dist = math.sqrt((ball_pos.x - proj_x)**2 + (ball_pos.y - proj_y)**2)
            
            # If distance less than ball radius, consider detected
            # Simplified: Larger detection tolerance for easier sensing
            if dist < self.ball_radius + 1.0:  # Ultra large tolerance (1.0m) - almost always detects
                # Check if within ray range
                if 0 <= t <= 1:
                    if dist < min_distance:
                        min_distance = dist
                        closest_ball = ball_data
        
        # Update sensor state
        if closest_ball:
            sensor['detected_object'] = closest_ball['body']
            sensor['detected_color'] = closest_ball['color'].upper()
        else:
            sensor['detected_object'] = None
            sensor['detected_color'] = 'NONE'
    
    def _update_logic_gates(self, time_step):
        """Update logic gate states"""
        for gate in self.logic_gates:
            if gate['type'] == 'AND':
                input_a_val = self._get_signal_value(gate['input_a'])
                input_b_val = self._get_signal_value(gate['input_b'])
                gate['output'] = input_a_val and input_b_val
            elif gate['type'] == 'OR':
                input_a_val = self._get_signal_value(gate['input_a'])
                input_b_val = self._get_signal_value(gate['input_b'])
                gate['output'] = input_a_val or input_b_val
            elif gate['type'] == 'NOT':
                input_val = self._get_signal_value(gate['input_a'])
                gate['output'] = not input_val
            elif gate['type'] == 'DELAY':
                # Delay: Add current input to buffer
                # Prefer input_signal_value (if exists), otherwise use input
                if 'input_signal_value' in gate:
                    input_val = gate['input_signal_value']
                else:
                    input_val = self._get_signal_value(gate['input'])
                
                # Only add to buffer when input changes from False to True (rising edge trigger)
                last_input = gate.get('last_input', False)
                if input_val and not last_input:
                    gate['buffer'].append((True, gate['delay']))
                gate['last_input'] = input_val
                
                # Update buffer (decrease time)
                new_buffer = []
                gate['output'] = False
                output_duration = gate.get('output_duration', 0.3)  # Output duration 0.3s
                for val, remaining_time in gate['buffer']:
                    remaining_time -= time_step
                    if remaining_time <= 0:
                        # Output delayed signal, maintain for a period
                        elapsed = -remaining_time  # Elapsed time
                        if elapsed <= output_duration:
                            gate['output'] = val
                            # Maintain output, continue tracking time until exceeds duration
                            new_buffer.append((val, remaining_time))
                        # Clear after exceeding duration (no longer add to new_buffer)
                    else:
                        new_buffer.append((val, remaining_time))
                gate['buffer'] = new_buffer
    
    def _get_signal_value(self, source):
        """Get signal source value"""
        if isinstance(source, dict):
            if 'detected_color' in source:  # Sensor
                # Check if red ball detected
                return source['detected_color'] == 'RED'
            elif 'output' in source:  # Logic gate
                return source['output']
            elif 'input_signal_value' in source:  # Delay input value
                return source['input_signal_value']
            elif 'active' in source:  # Actuator
                return source['active']
        return False
    
    def _update_actuators(self):
        """Update actuators based on logic gate output"""
        for wire in self.wires:
            source_val = self._get_signal_value(wire['source'])
            target = wire['target']
            
            if isinstance(target, dict) and 'active' in target:  # Piston
                # If signal is True, activate piston; otherwise deactivate
                self.activate_piston(target, source_val)
            elif isinstance(target, dict) and 'target_speed' in target:  # Motor
                # If signal is True, set speed; otherwise stop
                speed = target['current_speed'] if source_val else 0.0
                self.set_motor_speed(target, speed)
    
    def get_basket_bounds(self):
        """Get basket boundary information"""
        return {
            'red': self.red_basket,
            'blue': self.blue_basket
        }

