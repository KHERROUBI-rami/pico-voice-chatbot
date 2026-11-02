cmake_minimum_required(VERSION 3.13)

# Raspberry Pi Pico 2 W (RP2350 + Wi-Fi). Must be set BEFORE the SDK import.
set(PICO_BOARD pico2_w)

include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)

project(chatbot C CXX ASM)

pico_sdk_init()
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -include cstdint")

# TensorFlow Lite Micro for Pico (clone it into this folder: see steps)
add_subdirectory(pico-tflmicro)

add_executable(streaming streaming.cpp)

# so that fft.h, mfcc.h, kws.h, model.h, lwipopts.h are found
target_include_directories(streaming PRIVATE ${CMAKE_CURRENT_LIST_DIR})

target_link_libraries(streaming
    pico_stdlib
    pico_cyw43_arch_lwip_threadsafe_background
    pico-tflmicro
)

# printf() goes over the USB cable (not UART)
pico_enable_stdio_usb(streaming 1)
pico_enable_stdio_uart(streaming 0)

# produces streaming.uf2
pico_add_extra_outputs(streaming)



