cmake_minimum_required(VERSION 3.0 FATAL_ERROR)
project(autosvg-cli)

set(CMAKE_CXX_STANDARD 11)

IF (DEFINED ENV{OPENCV_SDK})
ELSE ()
    set(ENV{OPENCV_SDK} '../../third_party/opencv')
ENDIF ()

IF (DEFINED ENV{NUMCPP})
ELSE ()
    set(ENV{NUMCPP} '../../third_party/numcpp')
ENDIF ()

get_filename_component(opencv_base_dir $ENV{OPENCV_SDK}} ABSOLUTE)
get_filename_component(numcpp_dir $ENV{NUMCPP} ABSOLUTE)

file(GLOB opencv_include_modules "${opencv_base_dir}/modules/*/include")
file(GLOB_RECURSE autosvg-cli-executable "../cpp/AutosvgCLI.cpp" "../cpp/*/*.cpp")

set(Boost_INCLUDE_DIR "/usr/local/include")
set(Boost_USE_MULTITHREADED ON)
find_package(Boost 1.72.0 REQUIRED)

include_directories(${Boost_INCLUDE_DIRS})

include_directories(${numcpp_dir}/include)
include_directories(${opencv_include_modules})
include_directories("${opencv_base_dir}/include")
include_directories("${opencv_base_dir}/build_cli")

SET(LIBRARY_MODE_TARGET "MODULE")


file(GLOB opencv_libs "${opencv_base_dir}/build_cli/lib/*.dylib")
include_directories(../cpp)
add_executable(autosvg-cli ${autosvg-cli-executable})

target_link_libraries(autosvg-cli ${Boost_LIBRARIES})
target_link_libraries(autosvg-cli ${opencv_libs})

include(ExternalProject)
ExternalProject_Add(cxxopts
        GIT_REPOSITORY https://github.com/jarro2783/cxxopts
        GIT_TAG master
        SOURCE_DIR "${CMAKE_BINARY_DIR}/cxxopts-src"
        BINARY_DIR "${CMAKE_BINARY_DIR}/cxxopts-build"
        )


set(COMPILE_FLAGS "-Wno-missing-prototypes")

set_target_properties(autosvg-cli PROPERTIES COMPILE_FLAGS ${COMPILE_FLAGS})

