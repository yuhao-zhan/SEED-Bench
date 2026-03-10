# Category2_Kinematics_Linkages 任务变异总结表

## 任务概览

| 任务ID | 初始任务描述（一句话） | Stage-1 | Stage-2 | Stage-3 | Stage-4 |
|--------|----------------------|---------|---------|---------|---------|
| **K_01** | 设计连杆行走机构，仅靠电机转动在平地持续前进（至少10m，躯干不触地） | **Low Ground Friction**: 地面摩擦 0.8→0.04，极滑 | **Restricted Joint Limits**: 关节角度限制 ±π→±18° | **Friction + Joints**: 地面摩擦 0.5 + 关节 ±18° | **Extreme**: 重力 -20、地面摩擦 0.04、关节 ±15°、阻尼 2.0 |
| **K_02** | 设计攀墙机构，用电机与吸盘在垂直墙面上攀爬并到达红线高度 | **Low Wall Friction**: 墙面摩擦 1.0→0.12，易打滑 | **Increased Gravity**: 重力 -8→-20 m/s² | **Friction + Gravity**: 墙面摩擦 0.20 + 重力 -16 | **Extreme**: 墙面摩擦 0.14 + 重力 -20 + 吸盘力减弱（scale 35, max 22 N） |
| **K_03** | 设计夹爪机构，抓取地面物体并抬升到至少 y≥4m 并维持 2 秒 | **Slippery Object**: 物体表面摩擦 0.6→0.09 | **Heavy World**: 重力 -10→-17 m/s² | **Slippery + Heavy + Damping**: 摩擦 0.12 + 重力 -14 + 阻尼 0.75 | **Circular Object + Harsh Physics**: 物体圆形、摩擦 0.11、重力 -15、阻尼 0.6 |
| **K_04** | 设计推料机构，用电机驱动将重物沿高摩擦地面向前推动至少 8m | **High Tipping Hazard**: 物体质心上移 (0.1, 0.2)，极易向后倾覆 | **Sticky Terrain**: 地面高摩擦 (1.5) + 重载物体 (60kg) | **Slippery Ground**: 物体与地面摩擦极低 (0.1)，易打滑脱离 | **Low Gravity**: 低重力 (-2.0) + 低摩擦，物体易漂浮 |
| **K_05** | 设计剪刀式升降机构，将物体从地面抬升到至少 8m 高（y≥9m）并维持 3 秒 | **Severe Wind**: 强侧向风 (150N)，物体易被吹落 | **Ceiling Gap**: y=6m 处有 2m 宽窄缝天花板，限制平台宽度 | **Wind + Gap + Target**: 强风 (250N) + 窄缝 (2.4m) + 10.5m 目标 + 重载物体 (45kg) | **Extreme**: 强风 (200N) + 窄缝 (3m) + 10m 目标 + 低摩擦物体 (0.2) + 35kg 载荷 |
| **K_06** | 设计刮条机构，用电机驱动清除玻璃表面全部 45 颗粒子（100% 清除） | **More Particles + Layout**: 粒子 60 颗、seed 0 | **Stickier Particles**: 粒子摩擦 0.35→0.70 | **Strict Mass Limit**: 结构质量上限 15→0.25 kg（参考解超限） | **Combined**: 55 颗粒子、摩擦 0.55、seed 5 |

## 详细物理参数变化

### K_01: The Walker
- **初始**: 地面摩擦 0.8, 重力 -10, 关节限制 ±π
- **Stage-1**: `terrain_config: { ground_friction: 0.04 }`
- **Stage-2**: `physics_config: { default_joint_lower_limit: -π/10, default_joint_upper_limit: π/10 }`（±18°）
- **Stage-3**: `terrain_config: { ground_friction: 0.5 }` + 同上关节限制
- **Stage-4**: `terrain_config: { ground_friction: 0.04 }`, `physics_config: { gravity: (0, -20), max_body_friction: 0.15, default_joint_lower_limit: -π/12, default_joint_upper_limit: π/12, linear_damping: 2.0, angular_damping: 2.0 }`

### K_02: The Climber
- **初始**: 墙面摩擦 1.0, 重力 -8 m/s², 吸盘力约 55 N/个
- **Stage-1**: `terrain_config: { wall_friction: 0.12 }`
- **Stage-2**: `physics_config: { gravity: (0, -20.0) }`
- **Stage-3**: `terrain_config: { wall_friction: 0.20 }`, `physics_config: { gravity: (0, -16.0) }`
- **Stage-4**: `terrain_config: { wall_friction: 0.14 }`, `physics_config: { gravity: (0, -20.0), pad_force_scale: 35.0, max_pad_force: 22.0 }`

### K_03: The Gripper
- **初始**: 物体方盒、质量 1 kg、摩擦 0.6, 重力 -10
- **Stage-1**: `terrain_config: { objects: { shape: "box", mass: 1.0, friction: 0.09, x: 5.0, y: 2.0 } }`
- **Stage-2**: `physics_config: { gravity: (0, -17.0) }`（物体同默认）
- **Stage-3**: `terrain_config: { objects: { shape: "box", mass: 1.0, friction: 0.12, x: 5.0, y: 2.0 } }`, `physics_config: { gravity: (0, -14.0), linear_damping: 0.75, angular_damping: 0.75 }`
- **Stage-4**: `terrain_config: { objects: { shape: "circle", mass: 1.0, friction: 0.11, x: 5.0, y: 2.0 } }`, `physics_config: { gravity: (0, -15.0), linear_damping: 0.6, angular_damping: 0.6 }`（可见：物体为圆形）

### K_04: The Pusher
- **初始**: 地面摩擦 1.2, 重力 -10, 物体 50 kg、无质心偏移
- **Stage-1**: `terrain_config: { object: { center_of_mass_offset: (0.1, 0.2) } }`, `physics_config: { do_sleep: False }`
- **Stage-2**: `terrain_config: { ground_friction: 1.5, object: { mass: 60.0 } }`, `physics_config: { do_sleep: False }`
- **Stage-3**: `terrain_config: { ground_friction: 0.1, object: { friction: 0.1 } }`, `physics_config: { do_sleep: False }`
- **Stage-4**: `terrain_config: { ground_friction: 0.05 }`, `physics_config: { gravity: (0, -2.0), do_sleep: False }`

### K_05: The Lifter
- **初始**: 重力 -10, 物体 20 kg, 目标高度 y≥9 m（距地 8 m）, 地面摩擦 0.8
- **Stage-1**: `physics_config: { wind_force: (150.0, 0.0) }` (侧向强风)
- **Stage-2**: `terrain_config: { ceiling_gap: { x_min: 3.0, x_max: 5.0, y: 6.0 } }` (窄缝障碍)
- **Stage-3**: `terrain_config: { target_object_y: 10.5, object: { mass: 45.0 }, ceiling_gap: { x_min: 2.8, x_max: 5.2, y: 6.0 } }`, `physics_config: { wind_force: (250.0, 0.0) }`
- **Stage-4**: `terrain_config: { target_object_y: 10.0, object: { mass: 35.0, friction: 0.2 }, ceiling_gap: { x_min: 2.5, x_max: 5.5, y: 6.0 } }`, `physics_config: { wind_force: (200.0, 0.0) }`

### K_06: The Wiper
- **初始**: 45 颗粒子、seed 42、粒子摩擦 0.35、结构质量上限 15 kg；参考 agent 约 105k 步达 100% 清除
- **Stage-1**: `terrain_config: { particles: { count: 60, seed: 0, friction: 0.35, mass: 0.15 } }`
- **Stage-2**: `terrain_config: { particles: { count: 45, seed: 42, friction: 0.70, mass: 0.15 } }`
- **Stage-3**: `terrain_config: { max_structure_mass: 0.25, particles: { count: 45, seed: 42, friction: 0.35, mass: 0.15 } }`（参考刮条 ~0.29 kg，构建即失败）
- **Stage-4**: `terrain_config: { particles: { count: 55, seed: 5, friction: 0.55, mass: 0.15 } }`

## 变异模式总结

### 单一参数变化（Stage-1 / Stage-2）
- **K_01**: 地面摩擦 / 关节角度限制
- **K_02**: 墙面摩擦 / 重力
- **K_03**: 物体表面摩擦 / 重力
- **K_04**: 物体质心偏移 / 地面摩擦+物体质量
- **K_05**: Atmospheric Wind / Narrow Gap Obstacle
- **K_06**: 粒子数量与布局 / 粒子摩擦

### 两参数组合（Stage-3）
- **K_01**: 地面摩擦 + 关节限制
- **K_02**: 墙面摩擦 + 重力
- **K_03**: 物体摩擦 + 重力 + 阻尼
- **K_04**: 地面摩擦 + 物体摩擦
- **K_05**: Wind + Gap + Target Height + Heavy Mass
- **K_06**: 结构质量上限（导致参考解构建失败）

### 多参数组合（Stage-4）
- **K_01**: 重力 + 地面摩擦 + 关节限制 + 阻尼
- **K_02**: 墙面摩擦 + 重力 + 吸盘力减弱
- **K_03**: 物体形状（圆）+ 摩擦 + 重力 + 阻尼
- **K_04**: 地面摩擦 + 重力
- **K_05**: Wind + Gap + Target + Low Friction + Mass
- **K_06**: 粒子数量 + 粒子摩擦 + 布局 seed

## 说明

- 所有变异参数对求解器**不可见**（除 K_03 Stage-4 物体形状、K_05 目标高度为可见）。
- 参考 agent（各任务下 `agent.py`）在**初始环境**可通过测试，在**各 Stage 变异环境**下设计为无法通过，需重新设计或调参才能适应。
- K_03 在 `stages.py` 中另含 **baseline** 阶段（与初始任务一致），评估时仅使用 Stage-1～Stage-4 作为变异阶段。
