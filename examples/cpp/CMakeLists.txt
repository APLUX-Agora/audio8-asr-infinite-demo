cmake_minimum_required(VERSION 3.16)
project(audio8_file_example LANGUAGES CXX)

# Link the delivered SDK; never rebuild the inference library here.
get_filename_component(DEMO_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
set(AUDIO8_SDK_ROOT "${DEMO_ROOT}/sdk" CACHE PATH "Installed Audio8 SDK directory")
if(NOT EXISTS "${AUDIO8_SDK_ROOT}/lib/libaudio8_asr.so")
  message(FATAL_ERROR "Missing prebuilt SDK: ${AUDIO8_SDK_ROOT}/lib/libaudio8_asr.so")
endif()
add_library(audio8_asr SHARED IMPORTED)
set_target_properties(audio8_asr PROPERTIES
  IMPORTED_LOCATION "${AUDIO8_SDK_ROOT}/lib/libaudio8_asr.so"
  INTERFACE_INCLUDE_DIRECTORIES "${AUDIO8_SDK_ROOT}/include")
add_executable(transcribe_file transcribe_file.cpp)
target_compile_features(transcribe_file PRIVATE cxx_std_11)
target_compile_options(transcribe_file PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(transcribe_file PRIVATE audio8_asr)
set_target_properties(transcribe_file PROPERTIES
  BUILD_RPATH "${AUDIO8_SDK_ROOT}/lib")
