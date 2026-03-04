# Category1_Statics_Equilibrium 任务变异总结表

## 任务概览

| 任务ID | 初始任务描述（一句话） | Stage-1 | Stage-2 | Stage-3 | Stage-4 |
|--------|----------------------|---------|---------|---------|---------|
| **S_01** | 设计静态桥梁连接两个悬崖，让测试车辆通过 | **Wider Gap**: 间隙宽度 15m→18m | **Heavy Gravity**: 重力 -10→-15 m/s² | **Wider Gap + Lightweight**: 间隙18m + 最大质量 2000→1500kg | **Extreme Challenge**: 间隙20m + 重力-15 + 最大质量1200kg |
| **S_02** | 在狭窄基础上建造高层建筑，抵抗地震和风 | **Increased Amplitude**: 地震振幅 0.5→6.0m | **Increased Wind**: 风力 100→600N | **High-Frequency Earthquake**: 地震振幅 0.5→3.0m + 频率 2.0→8.0 Hz | **Perfect Storm**: 频率18.0 Hz + 振幅2.5m + 风力700N |
| **S_03** | 建造水平悬臂结构，仅锚定在左墙，双荷载（端部600kg+跨中400kg），到达14m，最多2锚点、扭矩≤2800Nm | **The Slalom Tunnel**: 多重障碍物形成狭窄蜿蜒通道，目标距离 25m | **Impact Resilience**: 动态掉落负载 (1000kg) + 重力 -15 m/s² | **The Weak Foundation**: 墙体锚固强度梯度分布 + 恒定横向风 + 重力 -18 m/s² | **The Perfect Storm**: 谐振垂直风 + 碎片化墙体支撑 + 动态掉落负载 + 极限跨度 35m + 重力 -20 m/s² |
| **S_04** | 在支点(0,0)上建造结构，平衡200kg不对称负载 | **Free Rotation + High Gravity**: 自由旋转 + 重力 -10→-13 m/s² | **Free Rotation + Low Damping**: 自由旋转 + 角阻尼 0.05 | **Free Rotation + High Friction**: 自由旋转 + 高摩擦2.0 + 低支点摩擦0.3 | **Extreme Physics**: 自由旋转 + 重力-15 + 极低阻尼0.02 + 高摩擦2.5 + 弹性0.4 + 平衡时间20s + 角度±8° |
| **S_05** | 保护脆弱核心免受来自左右两侧的坠落陨石撞击（15颗80kg，交替从左/右落下），核心70N，最大质量350kg | **Heavier Meteors**: 陨石质量 80→150kg | **Reduced Mass Budget**: 最大质量 350→120kg | **Gravity + Meteors**: 重力-60 + 陨石120kg | **Extreme Challenge**: 重力-16 + 地震(2.0 Hz, 4.0 m/s²) + 风力13 N/kg + 陨石110kg + 质量限制280kg + 核心55N |
| **S-06** | 在桌子上堆叠方块创建最大悬挑，仅使用重力和摩擦 | **Increased Gravity**: 重力 -10→-14 m/s² | **Reduced Friction**: 方块/桌面摩擦 0.5→0.08 | **Gravity + Friction**: 重力-13 + 方块/桌面摩擦0.18 | **Extreme Challenge**: 密度1.0→0.35 + 摩擦0.08 + 重力-17 + 无阻尼 |

## 详细物理参数变化

### S_01: The Bridge
- **初始**: 间隙15m, 重力-10, 最大质量2000kg
- **Stage-1**: `gap_width: 18.0`
- **Stage-2**: `gravity: (0, -15.0)`
- **Stage-3**: `gap_width: 18.0, max_structure_mass: 1500.0`
- **Stage-4**: `gap_width: 20.0, max_structure_mass: 1200.0, gravity: (0, -15.0)`

### S_02: The Skyscraper
- **初始**: 地震振幅0.5m, 频率2.0 Hz, 风力100N
- **Stage-1**: `earthquake_amplitude: 6.0` (仅改振幅)
- **Stage-2**: `wind_force: 600.0` (仅改风力)
- **Stage-3**: `earthquake_amplitude: 3.0, earthquake_frequency: 8.0` (振幅+频率)
- **Stage-4**: `earthquake_amplitude: 2.5, earthquake_frequency: 18.0, wind_force: 700.0` (组合)

### S_03: The Cantilever
- **初始**: 端部负载600kg(t=5s)、跨中负载400kg(t=10s, 节点近x=7.5m), 目标距离14m, 最多2锚点、锚点扭矩限制2800Nm
- **Stage-1**: `obstacle_rects: [[5,0,7,6], [10,8,12,20], [15,0,17,4]], target_reach: 25.0` (Slalom Tunnel)
- **Stage-2**: `load_type: "dropped", drop_height: 10.0, gravity: -15.0, target_reach: 25.0` (Impact Resilience)
- **Stage-3**: `anchor_strength_map: [...], wind_force: (500, 0), gravity: -18.0, target_reach: 28.0` (Weak Foundation)
- **Stage-4**: `wind_oscillatory: True, forbidden_anchor_y: [1, 4], anchor_strength_map: [...], drop_height: 12.0, target_reach: 35.0, gravity: -20.0` (The Perfect Storm)

### S_04: The Balancer
- **初始**: 刚性支点, 重力-10, 平衡时间15s, 角度±10°
- **Stage-1**: `force_pivot_joint: True, gravity: (0, -13.0)`
- **Stage-2**: `force_pivot_joint: True, angular_damping: 0.05, linear_damping: 0.05`
- **Stage-3**: `force_pivot_joint: True, pivot_friction: 0.3, friction: 2.0`
- **Stage-4**: `force_pivot_joint: True, balance_time: 20.0, max_angle_deviation_deg: 8.0, gravity: (0, -15.0), angular_damping: 0.02, linear_damping: 0.02, friction: 2.5, restitution: 0.4`

### S_05: The Shelter
- **初始**: 重力-10, 15颗陨石80kg（交替从左x∈[-5,-2]、右x∈[2,5]落下）, 核心70N, 最大质量350kg
- **Stage-1**: `meteor_mass: 150.0` (陨石加重)
- **Stage-2**: `max_mass: 120.0` (质量预算收紧)
- **Stage-3**: `meteor_mass: 120.0, gravity: (0, -60.0)` (重力+陨石)
- **Stage-4**: `meteor_mass: 110.0, max_mass: 280.0, core_max_force: 55.0, gravity: (0, -16.0), earthquake_enabled: True, earthquake_frequency: 2.0, earthquake_amplitude: 4.0, earthquake_direction: "horizontal", wind_enabled: True, wind_force: 13.0` (组合)

### S-06: The Overhang
- **初始**: 重力-10 m/s², 方块摩擦系数0.5, 桌面摩擦系数0.5, 材料密度1.0, 线性阻尼0.0, 角阻尼0.0
- **Stage-1**: `gravity: (0, -14.0)` (仅改重力)
- **Stage-2**: `block_friction: 0.08, table_friction: 0.08` (仅改摩擦)
- **Stage-3**: `block_friction: 0.18, table_friction: 0.18, gravity: (0, -13.0)` (重力+摩擦)
- **Stage-4**: `block_density: 0.35, block_friction: 0.08, table_friction: 0.08, gravity: (0, -17.0), linear_damping: 0.0, angular_damping: 0.0` (密度+摩擦+重力+无阻尼)

## 变异模式总结

### 单一参数变化（Stage-1/Stage-2）
- **S_01**: 间隙宽度 / 重力
- **S_02**: 地震振幅 / 风力
- **S_03**: 负载质量 / 目标距离
- **S_04**: 重力 / 阻尼
- **S_05**: 陨石质量 / 最大质量
- **S-06**: 重力 / 摩擦

### 两个参数组合（Stage-3）
- **S_01**: 间隙宽度 + 最大质量
- **S_02**: 地震振幅 + 频率
- **S_03**: 锚点强度 + 目标距离
- **S_04**: 自由旋转 + 高摩擦
- **S_05**: 重力 + 陨石质量
- **S-06**: 重力 + 摩擦

### 多个参数组合（Stage-4）
- **S_01**: 间隙宽度 + 重力 + 最大质量
- **S_02**: 地震频率 + 振幅 + 风力
- **S_03**: 负载 + 距离 + 重力 + 锚点强度
- **S_04**: 自由旋转 + 重力 + 阻尼 + 摩擦 + 弹性 + 时间 + 角度
- **S_05**: 重力 + 地震 + 风力 + 陨石质量 + 质量限制 + 核心强度
- **S-06**: 密度 + 摩擦 + 重力 + 阻尼
