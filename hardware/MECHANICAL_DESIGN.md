# 原创机械方案与SolidWorks建模输入

本文件是设计输入，不是已完成的SolidWorks装配或可直接激光切割的制造图。
采用单MG996驱动平行四连杆升降平台、左右被动导向，使台面提升时尽量保持水平。
电池低位居中，Pi与控制板分层；相机面向扫码方向，雷达不能被货架或升降台遮挡。
舵机输出轴只传转矩，货架重量由支撑轴/导向机构承担。设置上下机械限位，验证停机时
载荷不会因舵机失电自由落下。切勿根据未测载荷宣称MG996一定足够。

建模前记录：四轮最大外廓、轮宽、310电机安装孔、板卡孔距、雷达外形、MG996实际
舵盘半径、货架质量/重心/底部净空/内脚距/进入方向/可接触承载面、亚克力实测厚度。
机器人包括相机/雷达/电池/线缆应在300×300×180mm包络内。
优先将整机目标高度设为≤175mm留5mm制造余量；升降机构极限位置也必须检查包络。
URDF当前雷达顶高32.5+105+35=172.5mm仅为占位模型，实际传感器高度不能照抄。

设最大货架质量m，最不利负载臂r，效率η，机构力臂放大系数k；估算
`required_torque = m * 9.81 * r * k / η`，再按实测堵转/发热及设计裕量选连杆。
不得把舵机标称堵转转矩当持续可用转矩。升高距离应使货架最低点在全程保持正间隙，
包括地垫皱褶、加减速、侧移和转弯。台面只接触货架承重位置，不顶二维码标签。

建议SolidWorks装配结构：

```text
CourseRobot.SLDASM
  Chassis / BottomPlate.SLDPRT / MotorBrackets.SLDPRT
  Wheels / 4 wheels + adapters + 310 motors
  Lift / TopPlate / LinkPair / Guide / MG996Mount / LimitStops
  Electronics / Pi5 / MicroROSBoard / BatteryMount
  Sensors / MS200Mount / Camera3Mount
  Fasteners / Standoffs / CableStrainRelief
```

先参数化尺寸与配合，再验证干涉、轮子滚子间隙、满升程、扫码视野和装配工具空间。
平板导出1:1毫米DXF、3D打印支架导出STL，激光切割前用低成本样板测试孔位与kerf。
最终在SolidWorks用Pack-and-Go打包全部零件及引用，另一台电脑解压后打开装配检查
没有丢失引用；本仓库没有把URDF冒充SolidWorks模型。保留本组草图、设计迭代和计算
以支持原创性说明，不使用学长CAD代替自己的设计。
