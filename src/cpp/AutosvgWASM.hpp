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
    public:
        void loadImage(uintptr_t buffer, int rows, int cols);
        std::string convertToSvg();
    };
}


#endif //AUTOSVG_AUTOSVG_HPP
