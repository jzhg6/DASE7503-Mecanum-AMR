# Historical profile - wheel size and servo quantity superseded by teacher materials

Reference observation: `118ovo/DASE7503-Sem1-Group2`, commit
`d96b6071f32a5d04c0f529ada2d040119676eb1a`. The repository represents the
same course-provided hardware. Its implementation was inspected to identify
external hardware facts, but no C/C++/Python source or CAD asset was copied.

| Fact used by this project | Value | Status |
|---|---:|---|
| Controller | ESP32-S3 micro-ROS board | confirmed by prior build; inspect label |
| Motor PWM pairs FL/FR/RL/RR | 4/5, 15/16, 9/10, 13/14 | continuity-test before power |
| Encoder pairs FL/FR/RL/RR | 6/7, 47/48, 11/12, 1/2 | hand-turn verification required |
| Servo GPIO left/right | 8, 21 | verify connector labels |
| Encoder counts/output revolution | 1040 | measure one marked revolution |
| Wheel circumference | 150.8 mm | verify under working load |
| Full wheelbase / track used by prior controller | 95 / 135 mm | physical measurement required |
| MS200 serial settings | `/dev/oradar`, 230400 baud | verify udev symlink |
| LiDAR scan limits | 0.05-20 m, 10 Hz | manufacturer nominal |

## Values intentionally not treated as facts

- Motor and encoder signs: these depend on connector order and wheel mounting.
- PID gains: the repository provides conservative starting values, not copied
  tuning constants.
- Lift angles: only safe placeholders are present; linkage geometry must be
  calibrated with the horn detached.
- Acrylic outline, camera transform and loaded footprint: these must be measured
  from the built vehicle. The Xacro uses an independently drawn primitive model.
- Prior navigation screenshots and outcomes: they are not evidence for this
  project and must not appear as our experimental results.
