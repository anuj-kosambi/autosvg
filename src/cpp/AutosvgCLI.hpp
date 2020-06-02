
//
// Created by Anuj Kosambi on 2/06/20.
//

#ifndef AUTOSVG_AUTOSVG_HPP
#define AUTOSVG_AUTOSVG_HPP

#include <iostream>
#include <string>
#include <opencv2/opencv.hpp>
using namespace std;

namespace pi {
    class AutosvgCLI {
    private:
        cv::Mat *img;
        unsigned int *imagePixels;
        Pixel getContourColor(const Contour& contour);
    public:
        void loadImage(const string fileName);
        std::string convertToSvg(int k_colors, int sharpness);
        void writeImage(const string fileName);
    };
}

#endif //AUTOSVG_AUTOSVG_HPP
