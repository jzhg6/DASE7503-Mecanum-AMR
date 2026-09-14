# DASE7503 Autonomous Mecanum AMR

DASE7503 课程项目开发仓库：一台由 Raspberry Pi 和 ESP32 协同控制的麦克纳姆轮搬运小车，使用 LiDAR、相机和舵机完成建图定位、自动寻路、二维码任务识别与取放搬运。

> 当前状态：开发起点，尚非完成的实车项目。已加入 ROS 2 串口桥、QR 任务解析、仿真任务状态机和可编译 ESP32 骨架。没有在本机运行完整 ROS/Gazebo；电机和舵机输出均默认关闭，实车搬运任务默认拒绝执行。

当前欠缺：编码器/PID 与 odom/TF、实际型号的相机/LiDAR 驱动、对接控制、舵机完成反馈、载荷检测和实体搬运验证。上游升降服务只是 mock，平面运动插件也不模拟麦轮滚子接触物理；当前仿真成功不能作为载荷已被搬起的证据。

## 系统架构

```text
Camera -> QR reader -> Mission manager -> Nav2 -> /cmd_vel
                          |                         |
                          v                         v
                    lift services          mecanum_hw_bridge
                                                    |
                                              USB UART 115200
                                                    |
                                                  ESP32
                                         4 motor drivers + servo

LiDAR -> /scan -> SLAM Toolbox / AMCL -> map -> Nav2
Encoders (planned) -> ESP32 telemetry -> odometry / EKF
```

- Raspberry Pi：ROS 2、相机、二维码解析、任务调度、SLAM/AMCL、Nav2 和安全监控。
- ESP32：四轮 PWM、舵机、通信看门狗和最终急停执行。
- 笔记本：RViz、仿真、远程调试和日志分析；不应成为真实小车的安全依赖。

## 技术基线

- Ubuntu 22.04 64-bit + ROS 2 Humble，作为 2026 年秋季学期的冻结版本；Humble 官方支持到 2027 年 5 月。
- Gazebo Classic 11 遗留仿真基线（已停止维护，仅为复现实验保留）。
- Nav2 MPPI `Omni` 运动模型，允许麦轮横向速度 `vy`。
- ESP32 PlatformIO/Arduino 固件，通过 USB 串口与 Raspberry Pi 通信。

Humble 是当前参考代码的兼容基线，尚待与老师的系统镜像确认。如果使用 Raspberry Pi 5 或课程统一为 Ubuntu 24.04/Jazzy，应先核实镜像及驱动支持，再迁移 `ros_gz`/Gazebo Harmonic，不能把 Classic 插件直接用于新版 Gazebo。

## 目录

```text
src/
  mecanum_description/     URDF/Xacro：底盘、轮子、LiDAR、相机和搬运平台
  mecanum_simulation/      仓库世界与 QR 站点
  mecanum_navigation/      SLAM Toolbox、AMCL、Nav2 和地图
  mecanum_control/         麦轮运动学与仿真搬运机构
  mecanum_hw_bridge/       Raspberry Pi <-> ESP32 串口桥
  mecanum_task_manager/    QR 读取、任务解析和搬运状态机
firmware/esp32/             ESP32 安全固件骨架
hardware/                   协议及上游 STM32 参考实现
docs/                       课程范围、上游评估、架构和实车联调说明
```

## 快速开始

### 1. 安装与构建

```bash
sudo apt update
sudo apt install -y ros-humble-navigation2 ros-humble-nav2-bringup \
  ros-humble-slam-toolbox ros-humble-cv-bridge ros-humble-gazebo-ros-pkgs \
  python3-opencv python3-yaml python3-serial

mkdir -p ~/dase7503_ws/src
git clone git@github.com:jzhg6/DASE7503-Mecanum-AMR.git ~/dase7503_ws/src/DASE7503-Mecanum-AMR
cd ~/dase7503_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

### 2. 仿真启动入口（待 ROS 环境联调）

```bash
ros2 launch mecanum_bringup sim_bringup.launch.py \
  launch_navigation:=true launch_task_manager:=true
```

先建图并将 `stations.yaml` 的示例坐标替换为真实可达点，再发送任务。
当前世界内继承的 QR 纹理是旧坐标格式，不是下述任务格式；开发测试可发布 `/qr/data`，随后换成自己的 QR 图样。
`allow_mock_lift` 仅在仿真启动入口开启；任务协调器还要求 `use_sim_time=true`。实车入口不启用它。

示例任务二维码内容：

```json
{"mission_id":"M001","pickup":"RACK_A","dropoff":"RACK_B","item":"BOX_01"}
```

也支持更易手工生成的格式：

```text
mission_id:M001;pickup:RACK_A;dropoff:RACK_B;item:BOX_01
```

站点坐标在 `src/mecanum_task_manager/config/stations.yaml` 中维护。二维码只携带站点 ID，不直接信任任意坐标，可减少错误或恶意二维码让小车越界的风险。

### 3. 再接真实硬件

1. 按 `docs/HARDWARE_BRINGUP.md` 完成独立电源、共地、急停和架空轮测试。
2. 修改 `firmware/esp32/include/robot_config.h` 的引脚和电机方向。
3. 保持 `MOTOR_OUTPUT_ENABLED` 和 `SERVO_OUTPUT_ENABLED` 为 `0` 完成串口测试，再按实物分别配置引脚和开启输出。
4. 烧录 ESP32 后启动：

```bash
ros2 launch mecanum_hw_bridge real_robot_bringup.launch.py serial_port:=/dev/ttyUSB0
ros2 service call /safety/enable std_srvs/srv/Trigger '{}'
```

急停：

```bash
ros2 service call /safety/stop std_srvs/srv/Trigger '{}'
```

## 验收顺序

1. 单轮方向与急停。
2. 四轮前进、横移、旋转和 `/cmd_vel` 超时停车。
3. LiDAR TF、静态障碍物与手推建图。
4. AMCL 重定位和单点 Nav2。
5. 相机连续 QR 识别与去重。
6. 单次 `pickup -> lift -> dropoff -> lower -> home`。
7. 加入动态障碍、重复 QR、通信中断和低电压测试。

详细课程范围见 [docs/COURSE_PROJECT_SCOPE.md](docs/COURSE_PROJECT_SCOPE.md)，四个参考仓库的逐项取舍见 [docs/UPSTREAM_INTEGRATION.md](docs/UPSTREAM_INTEGRATION.md)。

## 安全与限制

- 不要用 L298N 直接驱动超过其电流能力的电机；按老师实际提供的电机堵转电流选择驱动器。
- 电机电源与 Raspberry Pi 5V 电源分开，逻辑地共地。
- 真实急停必须切断电机驱动使能或电机电源，ROS 服务只能作为第二层急停。
- 当前 ESP32 骨架是开环 PWM，不发布轮里程计；可靠定位和低速控制需要编码器闭环 PID。真实导航在 `/odom` 和 `odom -> base_footprint` 接通前不能工作。
- `Trigger.success` 目前只表示写出串口帧，不代表 MCU 接收或机械动作完成。
- 未测量底盘尺寸、轮径、减速比、编码器分辨率、舵机行程和 LiDAR 型号前，仓库中的数值只是安全起点。

## 来源与许可

本仓库以 MIT 许可的 `Trkkhrmn/ros2_amr_mecanumbot` 为代码基线并保留提交历史。`references/minibot/` 收录带许可的启动、SLAM、twist mux 样例，排除在当前构建之外；另外两个仓库以固定版本来源记录和独立实现整合。四个版本在 [upstreams.repos](upstreams.repos) 中锁定。详见 [来源评估](docs/UPSTREAM_INTEGRATION.md)、[许可记录](THIRD_PARTY_NOTICES.md) 和 [验证记录](docs/VALIDATION.md)。

## License

MIT。上游版权声明必须保留；参见 [LICENSE](LICENSE)。
