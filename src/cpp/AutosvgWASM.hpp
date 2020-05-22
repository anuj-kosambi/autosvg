//
// Created by Anuj Kosambi on 12/05/20.
//

#ifndef AUTOSVG_AUTOSVG_HPP
#define AUTOSVG_AUTOSVG_HPP

#include <emscripten.h>
#include <emscripten/bind.h>
#include <iostream>
#include <string>
#include <opencv2/opencv.hpp>

namespace pi {
    class AutosvgWASM {
    private:
        cv::Mat *img;
        unsigned int *imagePixels;
    public:
        void loadImage(uintptr_t buffer, int rows, int cols);

        std::string convertToSvg();
    };
}

EMSCRIPTEN_BINDINGS() {
    emscripten::class_<pi::AutosvgWASM>("AutosvgWASM")
            .constructor()
            .function("loadImage", &pi::AutosvgWASM::loadImage)
            .function("convertToSvg", &pi::AutosvgWASM::convertToSvg);
}

#endif //AUTOSVG_AUTOSVG_HPP
