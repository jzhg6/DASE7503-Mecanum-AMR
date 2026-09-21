# 2026-09-21 验证记录

本次依据老师项目文件重构。旧记录在 `history/VALIDATION-pre-teacher-spec.md`。

已验证：

- WSL Python：10项比赛规则测试，包括六种规定QR、无效码、重复START、错误后缀、
  四货架/独立卸货位/不回HOME、180秒精确边界、失败和迟到回调、实车尺寸/标定门槛。
- WSL gcc：纯C运动学、限速、编码器转换和PID核，`-Wall -Wextra -Werror`通过。
- 硬件表静态检查、Python语法与git diff空白检查通过。
- GitHub Actions #8，commit `cee749c`：Jazzy工作区构建/测试与ESP-IDF5.4.2
  ESP32-S3完整固件构建通过。不是仅控制核测试。
  https://github.com/jzhg6/DASE7503-Mecanum-AMR/actions/runs/35579907930

最新 GitHub Actions #10，commit `945a5e3`，三项作业全部成功：

- Jazzy `build-and-test`：3分19秒，工作区编译及colcon测试通过。
- `firmware-static-checks`：7秒，控制核及硬件配置检查通过。
- `esp32s3-firmware-build`：8分59秒，ESP-IDF5.4.2与锁定Jazzy micro-ROS依赖的
  ESP32-S3完整编译通过，已上传 `esp32s3-output-disabled` 固件产物。
- 运行记录：https://github.com/jzhg6/DASE7503-Mecanum-AMR/actions/runs/35599128070

最新CI覆盖：实际ROS Action/Service通信完成四件任务（24个导航目标、4次升/降），真实OpenCV从合成
二维码图像解码并写六类证据文件，以及Nav2七个真实插件节点的生命周期启动测试。
比赛截止使用稳态时钟，`use_sim_time`且没有`/clock`时也能计时。
最终串口配置为460800，固件的电机及舵机输出默认均禁用。
这些测试使用合成地图/雷达/图像或模拟执行器，不会生成冒充实车的比赛证据。

未做实物验收：Pi相机与libcamera实际兼容性、MS200驱动、串口电气和吞吐、轮序与PID、
尺寸与载货包络、单舵机负载能力、Nav2精确对接、货架离地/不碰墙/目的区真实件数。
完整清单见COURSE_ACCEPTANCE.md。CAD Pack-and-Go、实物和真实比赛证据尚未完成。
`presentation/DASE7503_Project_Design_20260921.pptx` 是可编辑的10页设计阶段汇报，正式展示前
仍需补本组CAD、实车测试结果及成员贡献。默认输出开关0，默认比赛配置未校准，不能直接下地运行。
