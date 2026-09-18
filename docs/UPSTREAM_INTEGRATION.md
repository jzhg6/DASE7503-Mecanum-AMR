# 四个参考仓库的取舍与整合

审阅于 2026-09-18 复核。所有上游都作为 Git remote 保留，便于查看更新，但只有明确授权的代码才可合并。

精确 commit 记录在 `upstreams.repos`；远程别名仅保存在本机 Git 配置，克隆本仓库时不会自动复制，使用该清单恢复即可。
本次实现的是“统一开发工作区 + 选定样例 + 来源锁定 + 移植骨架”，四套互不兼容的控制栈不会同时参与构建。

## 1. `118ovo/DASE7503-Sem1-Group2`

用户已确认该项目使用的就是本届获得的同款物理器材。因此它是硬件事实的首要参考，而不是本仓库的软件实现来源：

- `group4_codes.rar/group4_codes/group4_chassis_MicroROS/`：ESP32-S3、micro-ROS、四轮麦轮运动学、里程计和双舵机组织方式。
- `group4_codes.rar/group4_codes/group4_ws/src/qr_scanner/`：Raspberry Pi 相机截图与 QR 解码流程。
- `.../car_nav/` 与 `.../my_amcl_localization/`：Nav2 ActionClient、AMCL 和 map server 的最小用法。
- `.../team_proj2_pkg/`：四轮关节状态和 URDF 启动结构。
- `model&urdf.rar`：三层亚克力板、相机/LiDAR 安装、舵机搬运机构、DXF/STL 和 URDF 的对应方式。
- `QR scan picture.rar`：`START`、`RACKA-D`、`end` 等任务图样，可用于向老师确认本届 QR 语义是否沿用。

不直接采用：压缩包包含大量 `build/install/log` 产物、硬编码网络配置和未经说明的第三方 SDK；顶层没有 LICENSE。新实现只提取可外部验证的硬件事实，包括 ESP32-S3 GPIO、1040 count/rev、150.8 mm 轮周长、双舵机 GPIO 和 MS200 串口参数。运动学、PID、PCNT 采样、里程计、micro-ROS 生命周期、安全状态机、QR 流程和任务协议均重新编写。逐项记录见 `hardware/HARDWARE_PROFILE.md`。

## 2. `Trkkhrmn/ros2_amr_mecanumbot`

这是本仓库的 MIT 许可代码基线，直接保留并继续改造的部分：

- `mecanum_description`：LiDAR、相机、四麦轮和升降机构的 URDF/Xacro。
- `mecanum_simulation`：仓库世界、QR 站点和 Gazebo 启动。
- `mecanum_navigation`：SLAM Toolbox、AMCL、Nav2 参数和地图。
- `mecanum_control`：麦轮运动学和仿真升降。
- `mecanum_task_manager`：相机 QR 节点与任务状态机框架。
- `mecanum_hw_bridge`：保留包名，但 UART 实现已由 ESP32-S3 micro-ROS 监督器取代。
- `.github/workflows/ci.yml`：ROS 2 Humble 容器化构建测试。

必须修改的部分：上游实车是 Jetson Nano + STM32，而本项目是 Raspberry Pi + ESP32-S3 + 双舵机；完整自主链路主要在仿真验证。因此本仓库使用 micro-ROS 确认消息、编码器闭环、双层失效停车、受控任务 QR schema 和实车分阶段验收，不把仿真成功当作实车成功。

## 3. `YJ0528/minibot`

应参考但不照搬差速参数的部分：

- `launch/robot.launch.py` 与 `launch/robot_remote_station.launch.py`：把车载节点和远程 RViz/Nav2 控制站分开，降低 Raspberry Pi 负载。
- `launch/sim.launch.py` 与 `launch/sim_control_station.launch.py`：仿真端和控制端分层；SLAM、序列化地图定位和 AMCL 可切换。
- `description/ros2_control.xacro`、`config/controller*.yaml`：真实机/仿真共享 ros2_control 接口的组织方式。
- `config/twist_mux.yaml`：遥控优先级高于导航，适合调试和人工接管。
- `description/lidar.xacro`、`camera.xacro`、`depth_camera.xacro`：传感器拆分为独立 Xacro。
- `Tips_and_Troubleshooting.md`：TF、话题和参数排查方法。

不可直接套用：它是 ROS 2 Jazzy 的差速小车，轮模型、控制器、`vy=0` 限制和 Gazebo Harmonic 配置与本项目 Humble 麦轮基线不同。本仓库吸收“分层启动、twist mux、可切换定位”的设计，待实车稳定后再迁移 Jazzy。

已将上述选定启动文件、SLAM 参数、twist mux 参数、排障说明及原许可证放入 `references/minibot/`。真实车/远程站分工和人工接管仍是后续集成项。

## 4. `is-buiquocdoanh/mecanum_robot`

它的硬件组合与本项目最接近，重点参考：

- `src/ESP32_code/`：PlatformIO 项目布局、ESP32/CAN/电机控制的职责划分。
- `src/motor_control/`：`/cmd_vel` 到四轮 RPM、串口桥、编码器读取和超时归零。
- `src/robot_bringup/`：Raspberry Pi 与笔记本分别启动。
- `src/robot_mapping/`：Cartographer 配置。
- `src/robot_navigation/`：Nav2 参数、地图和 RViz。
- `src/ydlidar_ros2_driver/` 与 `src/rf2o_laser_odometry/`：特定 YDLIDAR 驱动和仅 LiDAR 里程计备选方案。
- `src/mecanum_joy/`：摇杆和速度多路复用。

不直接复制：仓库顶层没有统一 LICENSE，且代码包含硬编码串口、开环轮速、较弱的帧校验和板级专用参数。本仓库最终没有采用它的 ASCII 串口方案；实车链路以同款控制板支持的 ESP-IDF micro-ROS 为准。

## 最终整合映射

| 本仓库能力 | 主要来源 | 本项目改动 |
|---|---|---|
| 麦轮模型与仿真 | `ros2_amr_mecanumbot` | 缩小默认几何、集中标定参数 |
| SLAM/AMCL/Nav2 | `ros2_amr_mecanumbot` + `minibot` | Omni AMCL 与 MPPI、真实/远程分层路线 |
| Raspberry Pi-ESP32 链路 | 往届同款硬件事实 | 独立 ESP-IDF/micro-ROS 固件、安全确认和双舵机协议 |
| QR 识别 | `ros2_amr_mecanumbot` + 往届流程 | 连续相机话题、去重窗口、受控任务 schema |
| 搬运任务 | `ros2_amr_mecanumbot` 状态机 | 站点 ID 白名单、任务 ID 去重、失败锁定 |
| 机械与制造 | 往届 `model&urdf.rar` | 不复制 CAD，以实测尺寸和基本几何重画 |
| 人工接管 | `minibot` / `mecanum_robot` | 作为下一阶段的 `twist_mux` 工作项 |

## 学术诚信与可追溯性

项目评分针对实际集成和测试。引用往届工作不等同于学术不端；报告应如实区分复用部分和团队贡献，并遵守老师后续发布的复用规则。

- MIT 上游文件保留原作者版权头；本项目改动由 Git 历史区分。
- 往届仓库不复制代码、CAD、QR 图片或 vendored SDK；硬件事实单独记录并在本车复核。
- 报告中应明确列出参考仓库、实际采用内容、修改点和本团队测试结果。
- 不应把上游仿真截图或实车结果当成本团队实验数据。

## 审阅中发现的具体集成问题

- 主基线的 `task_manager.py` 实际是 launch 内容；`state_machine.py` 仅定义状态。新 `mission_manager.py` 才连接 QR、Nav2 结果和 mock 升降流程。
- 主基线 `patrol_manager.py` 在等待结果后直接返回 True，未核实成功状态；新协调器检查 `STATUS_SUCCEEDED`、超时与失败锁定。
- 主基线升降节点只打印日志并成功返回。新硬件监督器要求 ESP32 确认命令，并明确声明该确认仍不是载荷反馈；实车任务默认禁止仅靠位姿对接。
- 原 `navigation.launch.py` 的 `slam_mode=false` 未实际启动 AMCL；已补 localization launch。
- 麦轮仅设置 AMCL Omni 不够；原 RPP 控制器不会利用横移，已给 MPPI `Omni` 参数起点，仍需实测调参。
- `minibot` 的 `DifferentialMotionModel`、MPPI `DiffDrive` 和速度平滑器 `vy=0` 不能照搬；原硬件控制器也不是 ESP32 四轮接口。
- `mecanum_robot` 的独立 encoder_reader 只输出计数日志；不能把它当成完成的 odometry 发布节点。

## 官方兼容性依据

- [ROS Humble 生命周期](https://docs.ros.org/en/humble/Releases.html)
- [Jazzy 的 Ubuntu 24.04 / ARM64 支持](https://docs.ros.org/en/jazzy/Installation/Alternatives/Ubuntu-Install-Binary.html)
- [Nav2 MPPI 的 Omni 模型与参数](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/controller_plugins/mppi_controller/configuring_mppic/)
- [Gazebo Classic 停止维护公告](https://classic.gazebosim.org/)
