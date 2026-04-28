# syntax=docker/dockerfile:1.6
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        python3 \
        python3-pip \
        python-is-python3 \
        libboost-all-dev \
        libopencv-dev \
        libcxxopts-dev \
        pkg-config \
        ca-certificates \
        xz-utils \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

# autosvg's CMakeLists.txt hardcodes Boost_INCLUDE_DIR="/usr/local/include"
# (macOS/Homebrew layout). Symlink Ubuntu's boost headers to satisfy it.
RUN ln -s /usr/include/boost /usr/local/include/boost

COPY . /src/autosvg

WORKDIR /src/autosvg

RUN git submodule update --init --recursive \
 || ( \
      rm -rf third_party/emsdk third_party/opencv third_party/NumCpp && \
      git clone --depth 1 https://github.com/emscripten-core/emsdk.git third_party/emsdk && \
      git clone --depth 1 https://github.com/opencv/opencv.git       third_party/opencv && \
      git clone --depth 1 https://github.com/dpilger26/NumCpp.git    third_party/NumCpp \
    )

# Slim opencv WASM build: only the modules autosvg actually uses
# (core + imgproc + imgcodecs). Parallelized via MAKEFLAGS.
COPY <<'EOF' /src/autosvg/build-slim.sh
#!/bin/bash
set -euo pipefail

export EMSDK=$(pwd)/third_party/emsdk
export OPENCV_SDK=$(pwd)/third_party/opencv
export NUMCPP=$(pwd)/third_party/NumCpp
export EMSCRIPTEN=$EMSDK/upstream/emscripten/
export MAKEFLAGS="-j$(nproc)"

# Replace the pinned (stale) emsdk with the latest upstream — the old
# script hardcodes 'master' for emscripten-releases, which has been
# renamed to 'main', breaking 'install latest'.
rm -rf "$EMSDK"
git clone --depth 1 https://github.com/emscripten-core/emsdk.git "$EMSDK"

"$EMSDK/emsdk" update-tags
python "$EMSDK/emsdk.py" install latest
python "$EMSDK/emsdk.py" activate latest
# shellcheck disable=SC1091
source "$EMSDK/emsdk_env.sh"

cd "$OPENCV_SDK"
# Use build_js.py only for cmake config (--config_only), then run make
# ourselves on the specific targets we need. This skips opencv_js
# bindings, which fail to compile against modern emsdk's c++17-only
# embind headers when opencv is pinned to an older commit.
python ./platforms/js/build_js.py build_wasm --build_wasm --config_only \
    --cmake_option=-DBUILD_opencv_js=OFF        \
    --cmake_option=-DBUILD_opencv_imgcodecs=ON  \
    --cmake_option=-DBUILD_opencv_calib3d=OFF   \
    --cmake_option=-DBUILD_opencv_dnn=OFF       \
    --cmake_option=-DBUILD_opencv_features2d=OFF\
    --cmake_option=-DBUILD_opencv_flann=OFF     \
    --cmake_option=-DBUILD_opencv_photo=OFF     \
    --cmake_option=-DBUILD_opencv_objdetect=OFF \
    --cmake_option=-DBUILD_opencv_video=OFF     \
    --cmake_option=-DBUILD_opencv_ml=OFF        \
    --cmake_option=-DBUILD_opencv_stitching=OFF \
    --cmake_option=-DBUILD_opencv_gapi=OFF      \
    --cmake_option=-DBUILD_TESTS=OFF            \
    --cmake_option=-DBUILD_PERF_TESTS=OFF       \
    --cmake_option=-DBUILD_DOCS=OFF             \
    --cmake_option=-DBUILD_EXAMPLES=OFF

# Build only the static libs autosvg actually links against.
cd "$OPENCV_SDK/build_wasm"
make -j"$(nproc)" opencv_core opencv_imgproc opencv_imgcodecs

cd /src/autosvg
# autosvg's CMakeLists targets c++11 but AutosvgWASM.hpp uses
# emscripten/bind.h which requires c++17. Also, the GLOB pulls in
# AutosvgCLI.cpp (a native CLI that needs cxxopts.hpp, unrelated to
# the WASM build). Patch both inline; original tree is unchanged.
sed -i \
    -e 's|set(CMAKE_CXX_STANDARD 11)|set(CMAKE_CXX_STANDARD 17)\nadd_compile_definitions(_LIBCPP_ENABLE_CXX17_REMOVED_BINDERS _LIBCPP_ENABLE_CXX17_REMOVED_UNARY_BINARY_FUNCTION)|' \
    -e 's|file(GLOB_RECURSE autosvg-wasm-executable "src/cpp/\*\.cpp")|file(GLOB_RECURSE autosvg-wasm-executable "src/cpp/*.cpp")\nlist(FILTER autosvg-wasm-executable EXCLUDE REGEX ".*AutosvgCLI\\\\.cpp$")|' \
    CMakeLists.txt

cmake -DCMAKE_TOOLCHAIN_FILE="${EMSDK}/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake" .
make -j"$(nproc)"
EOF

# Native CLI build — separate from the WASM build. Uses system opencv
# and cxxopts (apt-installed). Shares Operations.cpp / CurveUtils.cpp
# with the WASM target; NumCpp is already vendored via submodule init.
COPY <<'EOF' /src/autosvg/build-cli.sh
#!/bin/bash
set -euo pipefail

cd /src/autosvg

g++ -std=c++17 -O2 \
    -D_LIBCPP_ENABLE_CXX17_REMOVED_BINDERS \
    -D_LIBCPP_ENABLE_CXX17_REMOVED_UNARY_BINARY_FUNCTION \
    -Wno-deprecated-declarations \
    -I src/cpp \
    -I third_party/NumCpp/include \
    src/cpp/AutosvgCLI.cpp \
    src/cpp/core/Operations.cpp \
    src/cpp/utils/CurveUtils.cpp \
    $(pkg-config --cflags --libs opencv4) \
    -o autosvg

echo "Built: $(pwd)/autosvg"
./autosvg --help || true
EOF

RUN chmod +x build.sh build-slim.sh build-cli.sh

CMD ["bash", "build-slim.sh"]
