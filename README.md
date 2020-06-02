# AutoSvg
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-1-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

Autosvg is tracing tool, which can convert image format like (jpg,png,gif) into vector svg.
You can check your result here (Live Demo)[https://autosvg.now.sh]. 

### Building AutoSVG-WASM.js

-   Environment Setup 
--  TODO (Adding opencv, emscripten and numcpp into submodules)
```bash
#
# https://github.com/emscripten-core/emsdk.git
#
export EMSDK=< path to Emscripten SDK repo>
#
# https://github.com/opencv/opencv.git
#
export OPENCV_SDK=<path to opencv repo>
#
# https://github.com/dpilger26/NumCpp.git
#
export NUMCPP=<path to numcpp repo>
``` 

- Run cmake building script for emscripten tool chain via 
```bash
> sh build.sh
```   
- Run make command to complile source code and building WASM file.
```bash
> make
Scanning dependencies of target autosvg-wasm
[ 25%] Building CXX object CMakeFiles/autosvg-wasm.dir/src/cpp/AutosvgWASM.cpp.o
[ 50%] Building CXX object CMakeFiles/autosvg-wasm.dir/src/cpp/core/Operations.cpp.o
[ 75%] Building CXX object CMakeFiles/autosvg-wasm.dir/src/cpp/utils/CurveUtils.cpp.o
[100%] Linking CXX executable autosvg-wasm.js
[100%] Built target autosvg-wasm 
```
- Copy wasm files to ui-app public folder. 
```bash
cp autosvg-wasm.* src/autosvg_ui/public
```

### Running AutoSVG-UI
```bash
> cd src/autosvg_ui/ && npm install
> npm run start 
```


## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="http://www.cwithabhas.com"><img src="https://avatars3.githubusercontent.com/u/3436431?v=4" width="60px;" alt=""/><br /><sub><b>Abhas Tandon</b></sub></a><br /><a href="https://github.com/anuj-kosambi/autosvg/commits?author=abhas9" title="Code">💻</a></td>
  </tr>
</table>

<!-- markdownlint-enable -->
<!-- prettier-ignore-end -->
<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!