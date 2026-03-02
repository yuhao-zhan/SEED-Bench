"""
S-02: The Skyscraper task Agent module
Build a tall tower that survives earthquake and wind
"""
import math


def build_agent(sandbox):
    """
    Build a tall skyscraper structure that can:
    1. Reach height > 30m
    2. Survive earthquake (horizontal oscillation starting at t=2s)
    3. Resist wind forces (100N lateral force above y=20m)
    4. Maintain stability (center of mass within x=[-4, 4])
    
    Strategy (基于物理分析):
    - 使用更粗的beam提高结构强度
    - 底部超重设计：使用超高密度beam降低质心
    - 超强连接：每个连接点使用多个joint确保结构完整性
    - 多层TMD系统：在不同高度放置调谐质量阻尼器减少振动
    - 渐缩设计：底部宽、顶部窄，减少风阻同时保持稳定性
    """
    # Foundation constraints
    FOUNDATION_X_MIN = -2.0
    FOUNDATION_X_MAX = 2.0
    TARGET_HEIGHT = 30.0
    MAX_WIDTH = 8.0
    
    # Design parameters - 使用更粗的beam提高稳定性
    BASE_WIDTH = 1.8  # Base width (within foundation)
    BEAM_HEIGHT = 0.8  # Height of each beam segment (适中的高度，平衡稳定性和连接点数量)
    BOTTOM_BEAM_WIDTH = 1.8  # Bottom section: WIDE
    MID_BEAM_WIDTH = 1.4  # Middle section: moderate width
    TOP_BEAM_WIDTH = 0.8  # Top section: narrow for wind
    NUM_LEVELS = 42  # Number of levels to reach >30m (42 * 0.8 = 33.6m)
    
    # 分段设计参数 - 更大的底部超重区域（降低质心）
    BOTTOM_SECTION_HEIGHT = 20.0  # Bottom 20m: VERY HEAVY (降低质心)
    MID_SECTION_HEIGHT = 30.0  # Middle section: normal
    # Top section: remaining height (约3-4m)
    
    # Start building from foundation
    foundation_y = 1.0  # Foundation top is at y=1.0
    
    # Build MULTIPLE base beams for ultra-strong foundation
    # 使用多个底部beam，形成更宽的支撑基础
    base_center_x = 0.0  # Center on foundation
    base_beams = []
    
    # Create multiple base beams side by side for wider foundation
    num_base_beams = 3
    base_spacing = BOTTOM_BEAM_WIDTH / (num_base_beams + 1)
    for i in range(num_base_beams):
        base_x = base_center_x - BOTTOM_BEAM_WIDTH/2 + (i + 1) * base_spacing
        base_y = foundation_y + BEAM_HEIGHT * 1.5  # Taller base
        
        base_beam = sandbox.add_beam(
            x=base_x,
            y=base_y,
            width=BOTTOM_BEAM_WIDTH / num_base_beams * 0.9,  # Slightly narrower to fit
            height=BEAM_HEIGHT * 3.0,  # Make base much taller (3倍高度)
            angle=0,
            density=20.0  # Extremely high density to significantly lower center of mass
        )
        base_beams.append(base_beam)
        
        # Anchor each base beam to foundation - CRITICAL for stability
        foundation = sandbox._terrain_bodies.get("foundation")
        if foundation:
            # Anchor at multiple points for each base beam
            num_anchors_per_beam = 7
            beam_width = BOTTOM_BEAM_WIDTH / num_base_beams * 0.9
            for j in range(num_anchors_per_beam):
                anchor_x = base_x - beam_width/2 + (j * beam_width / max(1, num_anchors_per_beam - 1))
                sandbox.add_joint(
                    foundation,
                    base_beam,
                    (anchor_x, foundation_y),
                    type='rigid'
                )
    
    # Connect base beams together with MANY joints for ultra-strong foundation
    for i in range(len(base_beams) - 1):
        beam_a = base_beams[i]
        beam_b = base_beams[i + 1]
        connection_y = foundation_y + BEAM_HEIGHT * 1.5
        connection_x = (beam_a.position.x + beam_b.position.x) / 2.0
        
        # Use many joints to connect base beams
        num_connection_joints = 9
        for j in range(num_connection_joints):
            joint_y = connection_y - BEAM_HEIGHT * 1.5 + (j * BEAM_HEIGHT * 3.0 / max(1, num_connection_joints - 1))
            sandbox.add_joint(
                beam_a,
                beam_b,
                (connection_x, joint_y),
                type='rigid'
            )
    
    # Use the middle base beam as the main base
    base_beam = base_beams[len(base_beams) // 2]
    
    previous_beam = base_beam
    previous_y = foundation_y + BEAM_HEIGHT * 1.5
    
    # Build vertical tower - 分段不同密度和宽度
    # Include all base beams in the beams list
    beams = list(base_beams)
    
    for i in range(1, NUM_LEVELS):
        current_y = previous_y + BEAM_HEIGHT
        
        # 分段设计：底部超重，中部正常，顶部轻质
        if current_y <= BOTTOM_SECTION_HEIGHT:
            # Bottom section: VERY HEAVY (大幅降低质心)
            # 使用渐缩：从底部1.8m逐渐变窄到1.4m
            taper_ratio = (BOTTOM_SECTION_HEIGHT - current_y) / BOTTOM_SECTION_HEIGHT
            current_width = MID_BEAM_WIDTH + (BOTTOM_BEAM_WIDTH - MID_BEAM_WIDTH) * taper_ratio
            current_density = 12.0  # Extremely high density
        elif current_y <= MID_SECTION_HEIGHT:
            # Middle section: moderate width and weight
            # 从1.4m渐缩到0.8m
            mid_taper_ratio = (MID_SECTION_HEIGHT - current_y) / (MID_SECTION_HEIGHT - BOTTOM_SECTION_HEIGHT)
            current_width = TOP_BEAM_WIDTH + (MID_BEAM_WIDTH - TOP_BEAM_WIDTH) * (1 - mid_taper_ratio)
            current_density = 8.0  # High density
        else:
            # Top section: narrow for wind resistance
            current_width = TOP_BEAM_WIDTH
            current_density = 5.0  # Moderate density
        
        current_beam = sandbox.add_beam(
            x=base_center_x,
            y=current_y,
            width=current_width,
            height=BEAM_HEIGHT,
            angle=0,
            density=current_density
        )
        
        # Connect with MANY joints for maximum strength
        connection_y = previous_y + BEAM_HEIGHT / 2
        
        # Use 25 joints per connection for ULTRA-STRONG connection
        # 超多连接点 = 超强的结构完整性（防止在地震中分离）
        num_joints = 25
        for j in range(num_joints):
            joint_x = base_center_x - current_width/2 + (j * current_width / max(1, num_joints - 1))
            sandbox.add_joint(
                previous_beam,
                current_beam,
                (joint_x, connection_y),
                type='rigid'
            )
        
        # Also connect to all base beams for bottom section (extra stability)
        if current_y <= BOTTOM_SECTION_HEIGHT and len(base_beams) > 1:
            for base_b in base_beams:
                if base_b != previous_beam:
                    # Add diagonal connections for extra stability
                    sandbox.add_joint(
                        base_b,
                        current_beam,
                        (base_center_x, connection_y),
                        type='rigid'
                    )
        
        beams.append(current_beam)
        previous_beam = current_beam
        previous_y = current_y
    
    # Add MULTIPLE tuned mass dampers at different heights (多层TMD系统)
    top_beam = beams[-1]
    top_y = previous_y
    
    # TMD系统优化：使用多个TMD，精确调谐到地震频率
    # TMD理论：频率应该接近但略低于激励频率，阻尼比应该较高
    # 地震频率：2.0 Hz
    
    # TMD 1: Top damper - 主要阻尼器（调谐到地震频率2.0 Hz）
    top_damper = sandbox.add_beam(
        x=base_center_x,
        y=top_y + 0.6,
        width=1.0,
        height=1.0,
        angle=0,
        density=2.0  # Heavier mass for more effective damping
    )
    
    sandbox.add_spring(
        top_beam,
        top_damper,
        (base_center_x, top_y + BEAM_HEIGHT / 2),
        (0, 0),
        stiffness=1.85,  # Slightly below earthquake frequency (2.0 Hz) for optimal damping
        damping=0.95  # Maximum damping
    )
    
    # TMD 2: Upper 3/4 height damper
    upper_level = int(NUM_LEVELS * 3 / 4)
    if upper_level > 0 and upper_level < len(beams):
        upper_beam = beams[upper_level]
        upper_y = foundation_y + (upper_level * BEAM_HEIGHT) + BEAM_HEIGHT / 2
        
        upper_damper = sandbox.add_beam(
            x=base_center_x,
            y=upper_y + 0.5,
            width=0.6,
            height=0.6,
            angle=0,
            density=1.5
        )
        
        sandbox.add_spring(
            upper_beam,
            upper_damper,
            (base_center_x, upper_y),
            (0, 0),
            stiffness=1.9,
            damping=0.9
        )
    
    # TMD 3: Mid-height damper (1/2 height)
    mid_level = NUM_LEVELS // 2
    if mid_level > 0 and mid_level < len(beams):
        mid_beam = beams[mid_level]
        mid_y = foundation_y + (mid_level * BEAM_HEIGHT) + BEAM_HEIGHT / 2
        
        mid_damper = sandbox.add_beam(
            x=base_center_x,
            y=mid_y + 0.4,
            width=0.5,
            height=0.5,
            angle=0,
            density=1.2
        )
        
        sandbox.add_spring(
            mid_beam,
            mid_damper,
            (base_center_x, mid_y),
            (0, 0),
            stiffness=1.95,
            damping=0.85
        )
    
    # TMD 4: Lower 1/4 height damper (额外阻尼)
    lower_level = int(NUM_LEVELS / 4)
    if lower_level > 0 and lower_level < len(beams):
        lower_beam = beams[lower_level]
        lower_y = foundation_y + (lower_level * BEAM_HEIGHT) + BEAM_HEIGHT / 2
        
        lower_damper = sandbox.add_beam(
            x=base_center_x,
            y=lower_y + 0.3,
            width=0.4,
            height=0.4,
            angle=0,
            density=1.0
        )
        
        sandbox.add_spring(
            lower_beam,
            lower_damper,
            (base_center_x, lower_y),
            (0, 0),
            stiffness=2.0,
            damping=0.8
        )
    
    # Calculate expected height
    expected_height = top_y + BEAM_HEIGHT / 2
    print(f"Skyscraper constructed: {len(base_beams)} base beams, {len(beams)} main beams, 4 TMD dampers, expected height ~{expected_height:.2f}m")
    
    # Debug: Check structure bounds immediately after construction
    bounds = sandbox.get_structure_bounds()
    print(f"Immediate structure bounds: top={bounds['top']:.2f}m, width={bounds['width']:.2f}m, center_x={bounds['center_x']:.2f}m")
    
    # Debug: Check if structure is stable
    if len(beams) > 0:
        print(f"Base beam position: x={base_beam.position.x:.2f}m, y={base_beam.position.y:.2f}m")
        if len(beams) > 1:
            print(f"Top beam position: x={beams[-1].position.x:.2f}m, y={beams[-1].position.y:.2f}m")
    
    return base_beam


def agent_action(sandbox, agent_body, step_count):
    """
    Agent control logic - optional dynamic adjustments
    For this task, we rely on passive damping, so no active control needed
    """
    pass
