cmake_minimum_required(VERSION 3.22)
project(single_motor_bench C ASM)
set(CMAKE_C_STANDARD 11)
set(BASELINE "$ENV{STM32_BASELINE_DIR}" CACHE PATH "仓库外只读 STM32 HAL 基线，必须显式指定")
if(NOT EXISTS "${BASELINE}/Drivers/STM32F1xx_HAL_Driver/Inc/stm32f1xx_hal.h" OR
   NOT EXISTS "${BASELINE}/startup_stm32f103xb.s" OR
   NOT EXISTS "${BASELINE}/STM32F103xx_FLASH.ld")
    message(FATAL_ERROR "缺少外部 test01 基线；使用 -DBASELINE=/absolute/path/to/test01。公共仓库不分发 HAL/启动/链接文件。")
endif()
get_filename_component(FW "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
set(HAL "${BASELINE}/Drivers/STM32F1xx_HAL_Driver")
add_executable(single_motor_bench.elf bench_main.c
    "${BASELINE}/startup_stm32f103xb.s"
    "${BASELINE}/Core/Src/system_stm32f1xx.c"
    "${BASELINE}/Core/Src/sysmem.c"
    "${BASELINE}/Core/Src/syscalls.c")
foreach(module motor encoder pid command telemetry bench)
    target_sources(single_motor_bench.elf PRIVATE "${FW}/${module}/${module}.c")
    target_include_directories(single_motor_bench.elf PRIVATE "${FW}/${module}")
endforeach()
target_sources(single_motor_bench.elf PRIVATE "${FW}/command/line_receiver.c")
foreach(driver hal hal_gpio hal_gpio_ex hal_tim hal_tim_ex hal_uart hal_rcc hal_rcc_ex hal_cortex hal_pwr hal_flash hal_flash_ex hal_exti hal_dma)
    target_sources(single_motor_bench.elf PRIVATE "${HAL}/Src/stm32f1xx_${driver}.c")
endforeach()
target_include_directories(single_motor_bench.elf PRIVATE "${BASELINE}/Core/Inc" "${HAL}/Inc"
    "${BASELINE}/Drivers/CMSIS/Include" "${BASELINE}/Drivers/CMSIS/Device/ST/STM32F1xx/Include")
target_compile_definitions(single_motor_bench.elf PRIVATE USE_HAL_DRIVER STM32F103xB)
target_compile_options(single_motor_bench.elf PRIVATE -Wall -Wextra -Os -g -fstack-usage)
target_link_options(single_motor_bench.elf PRIVATE -mcpu=cortex-m3 -mthumb --specs=nano.specs --specs=nosys.specs
    "-T${BASELINE}/STM32F103xx_FLASH.ld" -Wl,--gc-sections -Wl,-Map=single_motor_bench.map -u _printf_float)
target_link_libraries(single_motor_bench.elf PRIVATE m)
add_custom_command(TARGET single_motor_bench.elf POST_BUILD
    COMMAND arm-none-eabi-size $<TARGET_FILE:single_motor_bench.elf>)
