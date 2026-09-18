# Third-party notices

## Trkkhrmn/ros2_amr_mecanumbot

This repository was initially based on `Trkkhrmn/ros2_amr_mecanumbot`.

- Source: https://github.com/Trkkhrmn/ros2_amr_mecanumbot
- License: MIT
- Copyright: 2025 Tarik Kahraman

Files retaining an upstream copyright header remain under that notice. The root `LICENSE` contains the MIT terms.

## YJ0528/minibot

- Source: https://github.com/YJ0528/minibot
- License: MIT
- Copyright: 2024 YJ0528

Selected unmodified launch, SLAM, twist-mux and troubleshooting files are included
in `references/minibot/`, outside the active build. The original MIT license and
previous-license record are included alongside them.

## Reference-only repositories

The following repositories had no clear top-level license when reviewed on 2026-09-14, so their code and assets were not copied:

- https://github.com/118ovo/DASE7503-Sem1-Group2
- https://github.com/is-buiquocdoanh/mecanum_robot

Their high-level design ideas and relevant paths are documented in `docs/UPSTREAM_INTEGRATION.md` for independent reimplementation and academic attribution.

For `118ovo/DASE7503-Sem1-Group2`, the user later confirmed that its physical
parts match the supplied project kit. The new ESP32-S3 implementation therefore
uses documented hardware facts such as GPIO assignments, encoder resolution,
wheel circumference and sensor settings. It does not include that repository's
source code, CAD files, QR images or vendored SDK; the clean-room boundary is
recorded in `hardware/HARDWARE_PROFILE.md`.
