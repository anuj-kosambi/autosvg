//
// Created by Anuj Kosambi on 12/05/20.
//

#include "AutosvgWASM.hpp"

using namespace std;
using namespace cv;
using namespace emscripten;


namespace pi {
    void AutosvgWASM::loadImage(uintptr_t buffer, int rows, int cols) {
        try {
            auto *imagePixels = reinterpret_cast<unsigned int *>(buffer);
            cv::Mat frame(rows, cols, CV_8UC3, imagePixels);
            img = &frame;
            cout << "Image Size " << img->rows << " x " << img->cols << endl;
        } catch (const char *message) {
            cout << "Error in loading image : %s" << message << endl;
        }
    }

    string AutosvgWASM::convertToSvg() {
        return "<svg/>";
    }
}