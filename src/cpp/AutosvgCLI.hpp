
//
// Created by Anuj Kosambi on 2/06/20.
//

#ifndef AUTOSVG_AUTOSVG_HPP
#define AUTOSVG_AUTOSVG_HPP

#include <iostream>
#include <string>
#include <opencv2/opencv.hpp>

#include <utils/CurveUtils.hpp>
#include <utils/Constants.hpp>
#include <core/Operations.hpp>

using namespace cv;
using namespace std;

namespace pi {
    class AutosvgCLI {
    private:
        Pixel getContourColor(const Contour& contour);
    public:
        string inputFileName;
        string outputFileName;
        std::string convertToSvg(int k_colors, int sharpness);
        void writeImage(const string fileName, const string svgContent);
    };
}

#endif //AUTOSVG_AUTOSVG_HPP
