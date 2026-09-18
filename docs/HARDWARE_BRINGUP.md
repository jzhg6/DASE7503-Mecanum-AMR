# 实车联调手册

本仓库已经按同款课程硬件重构，但默认仍不能驱动电机或舵机：ESP32-S3
配置中的两个编译期开关均为 `0`。GPIO、编码器分辨率和 MS200 参数来自同款
硬件的公开资料，电机方向、舵机角度、有效轮径和机械尺寸必须在自己的实物上复核。

## 1. 接电前

- 将真实蘑菇急停串入电机驱动使能或电机电源；ROS 服务不能替代硬件急停。
- 电机、舵机和树莓派分路供电并共逻辑地，按堵转电流配置保险丝和限流。
- 用万用表核对 `hardware/HARDWARE_PROFILE.md` 的 GPIO 与板上接口。
- 将小车架空，拆下舵机连杆；首次烧录时不要接电机动力电源。

## 2. Linux 工具链与 micro-ROS

当前软件基线是 Ubuntu 22.04 / ROS 2 Humble。ESP-IDF 与 micro-ROS 也必须
使用兼容的 Humble 分支；不要同时运行 Jazzy Agent 和 Humble 固件。

```bash
# Raspberry Pi
source /opt/ros/humble/setup.bash
ros2 run micro_ros_agent micro_ros_agent udp4 --port 8090

# ESP32 开发环境
source ~/esp/esp-idf/export.sh
cd firmware/esp32
idf.py set-target esp32s3
idf.py menuconfig
idf.py build flash monitor
```

Wi-Fi 名称、密码、Agent IP、端口和 Domain ID 通过 `idf.py menuconfig` 设置，
不得提交到 Git。无动力状态下确认以下话题出现：

```bash
ros2 topic list | grep -E 'wheel/odom|base/enabled|lift/state'
ros2 topic hz /wheel/odom
```

## 3. 编码器与轮序

保持 `MOTOR_OUTPUT_COMPILED_IN 0`，依次手转 FL、FR、RL、RR。只有对应轮速
应改变；车轮朝“使车辆前进”的方向转动时，测得速度应为正。若符号错误，只改
对应的 `ENCODER_*_DIRECTION`。标记轮胎并转动一整圈，确认约为 1040 count。

## 4. 单轮闭环与失效停车

确认物理急停有效后，将 `MOTOR_OUTPUT_COMPILED_IN` 改为 `1`，仍保持小车架空。
启动真实硬件栈并显式使能：

```bash
ros2 launch mecanum_bringup real_bringup.launch.py \
  launch_sensors:=false launch_navigation:=false launch_task_manager:=false
ros2 service call /safety/enable std_srvs/srv/Trigger '{}'
```

用很小的 `/cmd_vel` 依次测试前进、横移和旋转。只在一个软件层修正电机方向。
停止发布后必须在 500 ms 内停车；关闭 Agent 或断开 Wi-Fi 后也必须停车并保持
未使能，直到再次调用 `/safety/enable`。

```bash
ros2 service call /safety/stop std_srvs/srv/Trigger '{}'
```

## 5. 几何、PID 与里程计

- 在载荷状态下测量轮子有效周长、前后轮中心距和左右轮中心距。
- 先分别调四轮低速 PID，再做四轮协调；避免用高增益掩盖轮序或机械问题。
- 用 2 m 直行、1 m 横移、360° 旋转校准轮径、横移误差和 `lx+ly`。
- 检查 `/odom` 与 `odom -> base_footprint` 连续且只有一个 TF 发布者。
- 麦轮在光滑地面容易横向打滑，编码器里程计误差不能用虚假的小协方差掩盖。

## 6. MS200 与相机

创建稳定的 `/dev/oradar` udev 链接后启动传感器：

```bash
ros2 launch mecanum_hw_bridge sensors.launch.py
ros2 topic hz /scan
ros2 topic hz /camera/image_raw
```

MS200 起点参数是 230400 baud、0.05-20 m、10 Hz。树莓派相机通过
`camera_ros/camera_node` 发布连续图像；不再用 `sudo rpicam-still` 循环截图。
若当前 Pi 相机只在 Raspberry Pi OS 的 `rpicam-*` 下工作，应先解决 libcamera
版本匹配，而不是让任务节点以 root 权限运行。

## 7. 双舵机与搬运

保持 `LIFT_OUTPUT_COMPILED_IN 0`，先用示波器或舵机测试仪确认 GPIO 8/21。
拆下连杆后确定左右舵机的安全上下角度，更新四个 `LIFT_*_DEG`，再开启编译开关。
调用 `/lift/up` 和 `/lift/down` 返回成功只代表固件确认命令，不代表抓住了货物。

实车任务还需要显式确认允许“仅靠导航位姿对接”：

```bash
ros2 launch mecanum_bringup real_bringup.launch.py \
  launch_navigation:=true launch_task_manager:=true \
  allow_pose_only_docking:=true
```

只有在每个站点的停靠误差和空载舵机动作都验收后才能打开该参数。二维码只携带
`stations.yaml` 中的站点 ID，不能直接给小车任意坐标。

## 8. 演示前检查

- [ ] 物理急停、`/safety/stop`、Wi-Fi/Agent 断开均已验证。
- [ ] 四轮方向、编码器方向、轮径、轮距和 PID 有本车测试记录。
- [ ] 地图、footprint、LiDAR/相机 TF 和站点坐标来自当前装配。
- [ ] 舵机供电独立，机械限位留有余量，空载动作重复可靠。
- [ ] 没有把 `/lift/state` 当作载荷传感器。
- [ ] 现场有人可立即断电，并保存本组自己的 rosbag、日志和录像。
