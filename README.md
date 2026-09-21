# DASE7503 2026-27 物流机器人

依据老师 2026-27 的四份 Group Project 文件修订。当前开发基线：Ubuntu 24.04
64-bit / ROS 2 Jazzy / Raspberry Pi 5 / ESP32-S3 micro-ROS USB 串口 / MS200 /
Camera Module 3 / 65 mm 麦轮 / 单个 MG996。GPIO 来自老师器材表，任务与固件独立编写；
保留原 MIT 上游许可。往届实现只用于接口研究，不能覆盖本届老师的规格。

## 当前实现

相机扫描 START 后启动 180 秒比赛；Nav2 使用雷达地图定位和导航，到达货架扫描位后，
必须读到对应货架及本组完整后缀才进入取货位。举升等待 MCU 确认并经过舵机稳定时间，
经退出位去 END 扫描位，再到独立卸货位放下货架、退出，继续下一件。四件完成或时间到即停止。
比赛期间不回 HOME。QR 图片和解码记录、任务状态日志保存在 `evidence/`。

实车启动有意要求完成标定：`course.yaml` 的 `calibrated: false`、空的本组二维码、
零值实测尺寸，以及固件输出开关均必须经过实测后填写。配置中的位姿仅用于软件测试。
目前采用“雷达定位 + 已标定取货位 + 到站相机身份核验”；没有实现二维码六自由度视觉伺服。
MG996 没有载荷反馈，完成指令序列不能证明货架已离地或成功落入目的区。

## 从这里开始

- [老师要求、冲突及对应实现](docs/COURSE_REQUIREMENTS.md)
- [Linux / 树莓派安装、串口与启动](docs/HARDWARE_BRINGUP.md)
- [逐项实车验收及提交清单](docs/COURSE_ACCEPTANCE.md)
- [机械方案、SolidWorks 建模约束](hardware/MECHANICAL_DESIGN.md)
- [本次验证记录](docs/VALIDATION.md)
- [四个上游的来源与许可](docs/UPSTREAM_INTEGRATION.md)

## 软件检查

```bash
# 在本仓库根目录；无需 ROS 的逻辑和控制核检查
python3 src/mecanum_task_manager/test/test_course_game.py
python3 firmware/esp32/host_test/test_hardware_profile.py
make firmware-host-test
# 已安装 Jazzy 后
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
colcon test --return-code-on-test-failure
colcon test-result --verbose
```

GitHub Actions 分别检查 Jazzy 工作区、比赛规则与 ESP32-S3 完整固件构建。
CI 不连接实车，不能证明实际完成三分钟比赛。旧 Humble/Gazebo Classic 仿真包被
`COLCON_IGNORE` 排除；`docs/history/` 和旧 patrol/mission 示例仅保留溯源，
不是本届部署入口。当前入口为 `real_bringup.launch.py` 和 `course.launch.py`。

老师要求的完整最终交付还包括实际装配测试、SolidWorks Pack-and-Go、PowerPoint、
六类二维码真实截图及器材归还。仓库提供程序与实施/验收文档，不能替代这些实物证据。
