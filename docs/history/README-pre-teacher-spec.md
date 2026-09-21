# 历史版本说明：已被 2026-27 老师项目规格取代，勿按此部署

DASE7503 课程项目开发仓库：Raspberry Pi 与 ESP32-S3 协同控制四轮麦克纳姆小车，
使用 ORADAR MS200、树莓派相机和双舵机完成建图定位、自动寻路、二维码任务识别
和取放搬运。

当前版本已经按往届项目使用的**同款硬件**重新设计底层，但不是往届代码的移植：
GPIO、编码器分辨率、轮周长和传感器接口作为硬件事实记录；ESP-IDF 固件、运动学、
PID、里程计、micro-ROS 生命周期、安全监督、QR 和任务流程均在本仓库独立实现。

> 状态：ROS 工作区和纯 C 控制核具备自动化构建验证；完整 ESP-IDF 固件仍需在
> Linux ESP-IDF/micro-ROS 工具链中构建，且尚未经过本组实车验收。电机和舵机输出
> 默认在编译期关闭；舵机没有位置/载荷传感器，不能把命令确认当成搬运成功。

## 架构

```text
Pi camera -> QR reader -> mission manager -> Nav2 -> /cmd_vel
                                |                         |
                                v                         v
                       lift/up|down services       ESP32-S3 micro-ROS
                                |                 wheel PID + watchdog
                                v                         |
                         /lift/command              /wheel/odom

MS200 -> /scan -> SLAM Toolbox / AMCL -> map       |
                                                     v
                              hardware supervisor -> /odom + odom TF
```

- Raspberry Pi：ROS 2、相机、QR、任务状态机、SLAM/AMCL、Nav2、TF 与硬件确认。
- ESP32-S3：编码器采样、四轮闭环 PID、里程计积分、双舵机和最终软件看门狗。
- 笔记本：RViz、仿真、调参和日志；不作为实车安全依赖。
- 物理急停：独立切断电机驱动使能或动力电源。

## 关键安全行为

- 固件的 `MOTOR_OUTPUT_COMPILED_IN`、`LIFT_OUTPUT_COMPILED_IN` 默认均为 `0`。
- ESP32 上电默认未使能；micro-ROS 断线或非法速度会停止并解除使能，
  `/cmd_vel` 超过 500 ms 则保持使能但强制轮速目标为零。
- `/safety/enable`、`/safety/stop`、`/lift/up`、`/lift/down` 等待 MCU 状态确认。
- `/wheel/odom` 经有限值和四元数检查后才发布为 `/odom` 和 TF。
- QR 只提供任务 ID 和站点 ID；坐标只从本地 `stations.yaml` 白名单读取。
- 实车“仅靠 Nav2 位姿对接”默认关闭，必须在标定后显式启用。

## 软件基线

- Ubuntu 22.04 64-bit + ROS 2 Humble。
- Gazebo Classic 11 仅用于现有仿真；它不模拟麦轮滚子和真实载荷接触。
- Nav2 MPPI `Omni` 模型，允许横向速度 `vy`。
- ESP-IDF + `micro_ros_espidf_component` Humble 分支，UDP Agent 默认端口 8090。
- `camera_ros/camera_node` 发布 `/camera/image_raw`。
- ORADAR MS200 驱动发布 `/scan`，默认 `/dev/oradar`、230400 baud。

不要混用 Humble 固件与 Jazzy Agent。若课程统一使用 Ubuntu 24.04/Jazzy，应整体迁移
ROS、Agent、micro-ROS 组件和仿真栈，而不是只替换其中一个组件。

## 目录

```text
firmware/esp32/             独立 ESP-IDF/micro-ROS 固件和主机单元测试
hardware/                   同款硬件事实、接口和失败边界
src/mecanum_description/    独立基本几何 Xacro；等待本车尺寸复核
src/mecanum_hw_bridge/      Agent、硬件确认服务、odom 与 TF 监督器
src/mecanum_navigation/     SLAM Toolbox、AMCL、全向 Nav2 和地图
src/mecanum_task_manager/   连续 QR 识别、白名单任务和搬运状态机
src/mecanum_simulation/     仓库世界与 QR 站点
docs/                       实车联调、来源取舍和验证记录
```

## 构建 ROS 工作区

```bash
sudo apt update
sudo apt install -y ros-humble-navigation2 ros-humble-nav2-bringup \
  ros-humble-slam-toolbox ros-humble-cv-bridge ros-humble-gazebo-ros-pkgs \
  ros-humble-micro-ros-agent ros-humble-camera-ros python3-opencv python3-yaml

mkdir -p ~/dase7503_ws/src
git clone git@github.com:jzhg6/DASE7503-Mecanum-AMR.git \
  ~/dase7503_ws/src/DASE7503-Mecanum-AMR
cd ~/dase7503_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

MS200 ROS 2 驱动可能需要按设备附带 SDK/官方仓库放进同一个工作区，包名和可执行文件
必须提供 `oradar_lidar/oradar_scan`。不要从往届压缩包复制未知许可的 vendored SDK。

## 仿真

```bash
ros2 launch mecanum_bringup sim_bringup.launch.py \
  launch_navigation:=true launch_task_manager:=true
```

示例任务二维码：

```json
{"mission_id":"M001","pickup":"RACK_A","dropoff":"RACK_B","item":"BOX_01"}
```

或：

```text
mission_id:M001;pickup:RACK_A;dropoff:RACK_B;item:BOX_01
```

## 实车启动

先完整执行 [实车联调手册](docs/HARDWARE_BRINGUP.md)。在无动力状态确认 Agent、
编码器、MS200 和相机后，启动基础栈：

```bash
ros2 launch mecanum_bringup real_bringup.launch.py \
  launch_navigation:=false launch_task_manager:=false
```

显式使能和急停：

```bash
ros2 service call /safety/enable std_srvs/srv/Trigger '{}'
ros2 service call /safety/stop std_srvs/srv/Trigger '{}'
```

完成地图、站点、轮速 PID、里程计和舵机验收后，才能运行真实任务：

```bash
ros2 launch mecanum_bringup real_bringup.launch.py \
  launch_navigation:=true launch_task_manager:=true \
  allow_pose_only_docking:=true
```

## 验收顺序

1. GPIO 连续性、编码器轮序/方向和物理急停。
2. 单轮 PID、四轮前进/横移/旋转和三类失效停车。
3. 2 m 直行、1 m 横移和 360° 旋转里程计标定。
4. MS200 TF、手推建图、AMCL 和单点 Nav2。
5. 相机连续 QR 识别、去重和非法任务拒绝。
6. 双舵机空载标定，再测试一次取货、送货、放下和回家。
7. 通信中断、动态障碍、重复二维码、低电压和急停恢复。

## 来源与学术诚信

往届同款硬件仓库是硬件事实参考，不是本仓库的代码来源。清洁重写边界和使用的事实
见 [HARDWARE_PROFILE.md](hardware/HARDWARE_PROFILE.md) 与
[UPSTREAM_INTEGRATION.md](docs/UPSTREAM_INTEGRATION.md)。MIT 基线及保留样例见
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。报告必须分别说明参考内容、本组实现、
本组标定数据和本组实验结果。

## License

MIT；上游版权与许可证见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
