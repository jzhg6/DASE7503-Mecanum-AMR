# ESP32-S3 / Jazzy / USB serial

独立实现的四轮编码器PID、里程计、停止联锁、单MG996举升与micro-ROS接口。
主机部署见 `../../docs/HARDWARE_BRINGUP.md`，接线见 `../../hardware/HARDWARE_PROFILE.md`。

在Linux ESP-IDF 5.4.2环境编译：

```bash
pip install catkin_pkg colcon-common-extensions lark empy==3.3.4
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyUSB0 flash
```

先通过设备序列号确认端口。固件使用UART0 115200 8N1，TX43/RX44；Jazzy组件锁定git
commit，`sdkconfig.defaults`选择自定义UART传输并关闭该串口日志。不可同时打开串口
monitor和Agent。Pi/PC都使用 `ROS_DOMAIN_ID=20`。

| 方向 | 接口 | 含义 |
|---|---|---|
| 订阅 | `/cmd_vel` Twist | m/s, m/s, rad/s；500ms无新命令清PID并停止PWM |
| 订阅 | `/base/enable` Bool | 编译输出开关开启后才能运行时使能 |
| 订阅 | `/lift/command` Int32 | 0放下/1举升；必须已使能且静止 |
| 发布 | `/wheel/odom` Odometry | 编码器里程计，20Hz |
| 发布 | `/base/enabled` Bool | 运行时使能状态，20Hz |
| 发布 | `/lift/state` Int32 | -1未知/动作中，0低，1高；等待1500ms后确认 |

上电不使能。失联、非法速度清使能；速度看门狗停车但保留使能以允许Nav2驻停扫码。
控制任务独占电机输出，最迟下一10ms周期执行停机。举升期间禁止底盘PWM输出。
计时结束保持当前舵机命令，不在运输途中主动卸货。完整固件构建不等于实物验收。
