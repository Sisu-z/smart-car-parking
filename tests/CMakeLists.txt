cmake_minimum_required(VERSION 3.22)
project(smart_car_host_tests C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
enable_testing()

set(FIRMWARE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../firmware")

add_library(smart_car_core STATIC
    "${FIRMWARE_ROOT}/motor/motor.c"
    "${FIRMWARE_ROOT}/encoder/encoder.c"
    "${FIRMWARE_ROOT}/pid/pid.c"
    "${FIRMWARE_ROOT}/command/command.c"
    "${FIRMWARE_ROOT}/command/line_receiver.c"
    "${FIRMWARE_ROOT}/bench/bench.c"
    "${FIRMWARE_ROOT}/telemetry/telemetry.c"
)
target_include_directories(smart_car_core PUBLIC
    "${FIRMWARE_ROOT}/motor"
    "${FIRMWARE_ROOT}/encoder"
    "${FIRMWARE_ROOT}/pid"
    "${FIRMWARE_ROOT}/command"
    "${FIRMWARE_ROOT}/bench"
    "${FIRMWARE_ROOT}/telemetry"
)
target_compile_options(smart_car_core PRIVATE -Wall -Wextra -Werror -pedantic)
option(ENABLE_SANITIZERS "主机地址/未定义行为检查" OFF)
if(ENABLE_SANITIZERS)
    target_compile_options(smart_car_core PUBLIC -fsanitize=address,undefined -fno-omit-frame-pointer)
    target_link_options(smart_car_core PUBLIC -fsanitize=address,undefined)
endif()
add_compile_options(-UNDEBUG)

function(add_smart_car_test target source)
    add_executable(${target} ${source})
    target_link_libraries(${target} PRIVATE smart_car_core m)
    target_compile_options(${target} PRIVATE -Wall -Wextra -Werror -pedantic)
    add_test(NAME ${target} COMMAND ${target})
endfunction()

add_smart_car_test(motor_open_loop_test motor_open_loop/test_motor_open_loop.c)
add_smart_car_test(encoder_count_test encoder_count/test_encoder_count.c)
add_smart_car_test(encoder_speed_test encoder_speed/test_encoder_speed.c)
add_smart_car_test(speed_pi_test speed_pi/test_speed_pi.c)
add_smart_car_test(command_telemetry_test command_telemetry_test.c)
add_smart_car_test(bench_safety_test bench_safety_test.c)
add_smart_car_test(numeric_edges_test numeric_edges_test.c)
add_executable(bench_host ../tools/bench_host.c)
target_link_libraries(bench_host PRIVATE smart_car_core m)
target_compile_options(bench_host PRIVATE -Wall -Wextra -Werror -pedantic)
