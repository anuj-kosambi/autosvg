cmake_minimum_required(VERSION 3.8)
project(autosvg-wasm)

set(CMAKE_CXX_STANDARD 11)

set(opencv_base_dir $ENV{OPENCV_SDK})

file(GLOB opencv_include_modules "${opencv_base_dir}/modules/*/include")
file(GLOB_RECURSE autosvg-wasm-executable "src/cpp/*.cpp")

set(Boost_INCLUDE_DIR "/usr/local/include")
set(Boost_USE_MULTITHREADED ON)
find_package(Boost 1.72.0 REQUIRED)

include_directories(${Boost_INCLUDE_DIRS})


include_directories($ENV{NUMCPP}/include)
include_directories(${opencv_include_modules})
include_directories(src/cpp)
include_directories("${opencv_base_dir}/include")
include_directories("${opencv_base_dir}/build_wasm")

add_executable(autosvg-wasm ${autosvg-wasm-executable})

file(GLOB opencv_libs_wasm "${opencv_base_dir}/build_wasm/lib/*.a")

target_link_libraries(autosvg-wasm ${Boost_LIBRARIES})

target_link_libraries(autosvg-wasm ${opencv_libs_wasm})
target_link_libraries(autosvg-wasm ${opencv_base_dir}/build_wasm/3rdparty/lib/libzlib.a)

set(COMPILE_FLAGS "-Wno-missing-prototypes")
set(EMSCRIPTEN_LINK_FLAGS "${EMSCRIPTEN_LINK_FLAGS} -s WASM=1")
set(EMSCRIPTEN_LINK_FLAGS "${EMSCRIPTEN_LINK_FLAGS} -s TOTAL_MEMORY=512MB")
set(EMSCRIPTEN_LINK_FLAGS "${EMSCRIPTEN_LINK_FLAGS} --bind")

set_target_properties(autosvg-wasm PROPERTIES COMPILE_FLAGS ${COMPILE_FLAGS})
set_target_properties(autosvg-wasm PROPERTIES LINK_FLAGS ${EMSCRIPTEN_LINK_FLAGS})


