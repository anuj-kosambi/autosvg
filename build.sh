#!/bin/bash

export EMSDK=./third_party/emsdk
export OPENCV_SDK=/third_party/opencv
export NUMCPP=/third_party/NumCpp

$EMSDK/emsdk update-tags
python $EMSDK/emsdk.py install latest
python $EMSDK/emsdk.py activate latest
source $EMSDK/emsdk_env.sh

cmake -DCMAKE_TOOLCHAIN_FILE=${EMSDK}/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake
