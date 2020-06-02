#!/bin/bash

export EMSDK=`pwd`/third_party/emsdk
export OPENCV_SDK=`pwd`/third_party/opencv
export NUMCPP=`pwd`/third_party/NumCpp
export EMSCRIPTEN=$EMSDK/upstream/emscripten/

$EMSDK/emsdk update-tags
python $EMSDK/emsdk.py install latest
python $EMSDK/emsdk.py activate latest
source $EMSDK/emsdk_env.sh

cd $OPENCV_SDK
python ./platforms/js/build_js.py build_wasm --build_wasm

cd .. && cd ..
cmake -DCMAKE_TOOLCHAIN_FILE=${EMSDK}/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake

echo $OPENCV_SDK
make
