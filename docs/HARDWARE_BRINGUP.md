# Ubuntu 24.04 / ROS 2 Jazzy 实车部署

以下命令在Linux执行，Windows无需安装ROS、ESP-IDF或PlatformIO。
本仓库使用Ubuntu24.04 arm64的Pi5与Jazzy；先按ROS官方安装说明安装Jazzy。
本机开发目录在E盘；Linux路径自行选择。所有终端统一：

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=20
cd /path/to/DASE7503-Mecanum-AMR
export ROS_LOG_DIR="$PWD/log/ros"
sudo apt install python3-colcon-common-extensions python3-rosdep python3-vcstool \
  python3-opencv python3-yaml ros-jazzy-nav2-bringup ros-jazzy-slam-toolbox \
  ros-jazzy-cv-bridge ros-jazzy-xacro
```

## 1. 相机和雷达驱动

老师器材文件p15要求 **libcamera和camera_ros均从源码构建**。
参考 [camera_ros官方源码构建说明](https://github.com/christianrauch/camera_ros#build-instructions)，
Ubuntu上的Camera3使用Raspberry Pi的libcamera fork。仓库 `hardware/camera.repos` 锁定
本次审阅版本，不代表已经在你这块Pi上验证。

```bash
mkdir -p external_ws/camera/src
vcs import external_ws/camera/src < hardware/camera.repos
sudo apt install python3-colcon-meson
cd external_ws/camera
rosdep install --from-paths src --ignore-src -y --rosdistro jazzy --skip-keys libcamera
colcon build --event-handlers console_direct+
source install/setup.bash
cd ../..
```

如果meson报告缺系统库，按Raspberry Pi/libcamera官方README安装相应依赖，勿把系统
libcamera二进制安装成功误认为已经满足老师的源码要求。
MS200使用[亚博供应商ROS2驱动说明](https://www.yahboom.net/public/upload/upload-html/1701163653/1.Preparation.html)
中的 `oradar_ros-dev-ros2` 软件包，单独工作区编译并source；预期包名 `oradar_lidar`、
可执行 `oradar_scan`，`ros2 pkg executables oradar_lidar`核对。
不从学长压缩包复制SDK。驱动未随本仓库vendoring，需要在Pi上安装并验证。

## 2. Agent与主工作区

在单独工作区从micro-ROS官方Jazzy setup生成Agent：

```bash
mkdir -p external_ws/agent/src
git clone -b jazzy https://github.com/micro-ROS/micro_ros_setup.git external_ws/agent/src/micro_ros_setup
cd external_ws/agent
rosdep install --from-paths src --ignore-src -y --rosdistro jazzy
colcon build
source install/setup.bash
ros2 run micro_ros_setup create_agent_ws.sh
ros2 run micro_ros_setup build_agent.sh
source install/setup.bash
cd ../..
rosdep install --from-paths src --ignore-src -y --rosdistro jazzy --skip-keys 'micro_ros_agent camera_ros'
colcon build --symlink-install
source install/setup.bash
```

新终端依次source Jazzy、camera工作区、MS200工作区、agent工作区和主仓库工作区。
确保 `ros2 pkg prefix micro_ros_agent`、`camera_ros`、`oradar_lidar`均成功。

## 3. 串口与固件

看 `firmware/esp32/README.md` 编译烧录。输出开关保持0，先确认串口通信、编码器和方向。
`ls -l /dev/serial/by-id/`分辨控制板与雷达；两个USB串口不可混用。将设备真实路径作为
launch参数；雷达端口在自己的hardware.yaml填写，使用udev持久命名时匹配设备序列号，
不要仅凭两个设备都具有同一USB芯片VID/PID就绑定。加入dialout组并重新登录。

```bash
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/serial/by-id/YOUR_ESP32 -b 115200
# 另一个已source的终端
ros2 launch mecanum_bringup real_bringup.launch.py launch_agent:=false \
  launch_sensors:=false
ros2 topic echo /base/enabled
ros2 topic echo /wheel/odom
```

架空手转轮验证计数和方向，校正GPIO对应轮位、x4计数、有效轮径、轴距/轮距与PID。
先单独标定MG996角度/连杆/举升时间，再开启相应编译开关并重新烧录。
正确接线：白色电机插头接控制板，黑色接310电机。不要用MG996信号脚供电。
老师的电池与控制板5V输出为最终电源；供电电缆和USB数据电缆是两根线。

## 4. 建图和参数标定

启用传感器，`/scan`与`/camera/image_raw`应持续发布。
`camera_ros`节点名必须为camera，使用私有图像接口`~/image_raw`。
先建图，不启动比赛：

```bash
ros2 launch mecanum_bringup real_bringup.launch.py \
  serial_device:=/dev/serial/by-id/YOUR_ESP32 launch_navigation:=true slam_mode:=true
ros2 service call /safety/enable std_srvs/srv/Trigger '{}'
# 低速遥控并保存空场静态地图；不要将可搬动货架永久写成静态障碍
ros2 run nav2_map_server map_saver_cli -f maps/course
```

第一次先`mkdir -p maps`。AMCL模式在RViz设置初始位姿并检查map→odom→base→lidar TF。
`course.yaml`样例不是老师的精确A-D坐标。复制为本组配置，标定每个扫描位、插入位、
退出位、END扫描位和四个卸货位。相机应在扫码位清楚看到二维码，取货后不要遮挡雷达。
如果从高精度停靠测试看Nav2误差大于机构容错，需要改进定位/机械导向或增加视觉对接，
不能只把`calibrated`改true。

复制 `src/mecanum_navigation/config/nav2_params.yaml` 为本组nav配置。两张costmap的
footprint均设置为机器人与所载货架的实测最大包络（含偏载及定位余量），并校准速度，
保守配置全程使用这个包络。当前样例仅机器人包络；不能直接载货比赛。
`collision_monitor`利用雷达扫描和同一footprint预测接触并减速/停机；雷达丢失也停止输出。
对接若被货架自身遮挡，调整物理雷达安装与机械进入方向，不能简单关掉避障绕过问题。

## 5. 比赛

在本组配置填入实际尺寸、四个完整二维码并完成验收后标记`calibrated: true`。
下列路径须指向自己的实测文件：

```bash
ros2 launch mecanum_bringup real_bringup.launch.py \
  serial_device:=/dev/serial/by-id/YOUR_ESP32 \
  launch_navigation:=true slam_mode:=false map_yaml:=/absolute/maps/course.yaml \
  nav2_params:=/absolute/config/nav2_calibrated.yaml \
  launch_task_manager:=true course_yaml:=/absolute/config/course_calibrated.yaml \
  evidence_dir:=/absolute/evidence/run01
ros2 service call /safety/enable std_srvs/srv/Trigger '{}'
ros2 topic echo /mission/status
```

机器人放入START区，确认AMCL定位，再让相机扫描真实START码。自动开始后无需人工
发布目标。不要比赛中使用`ros2 topic pub /qr/data`注入字符串：它是接口测试手段，不能
代替相机截图或老师要求的自动识别。
异常中止用 `ros2 service call /mission/abort std_srvs/srv/Trigger '{}'`；
确认底盘停止、人工恢复机构后用`/mission/reset`，重新摆车/使能/扫描START。
TIMEOUT保持升降位置，操作者稳妥处理未放下的货架。断电不是保证载物不落地的机械方案。
