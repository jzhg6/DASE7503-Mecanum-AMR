# Convenience targets for the DASE7503 Mecanum AMR.
# Requires: source install/setup.bash for run/test targets.

.PHONY: build test clean deps firmware-host-test

build:
	colcon build --symlink-install

test: build
	. install/setup.bash && colcon test --return-code-on-test-failure

firmware-host-test:
	mkdir -p build/host-tests
	$(CC) -std=c11 -Wall -Wextra -Werror \
		-Ifirmware/esp32/components/base_control/include \
		firmware/esp32/components/base_control/base_control.c \
		firmware/esp32/host_test/test_base_control.c -lm \
		-o build/host-tests/dase7503_base_control_test
	build/host-tests/dase7503_base_control_test

clean:
	rm -rf build install log

deps:
	rosdep update && rosdep install --from-paths src --ignore-src -r -y
