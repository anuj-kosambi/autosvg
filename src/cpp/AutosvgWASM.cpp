//
// Created by Anuj Kosambi on 12/05/20.
//

#include <core/Operations.hpp>
#include "AutosvgWASM.hpp"
#include <utils/CurveUtils.hpp>

using namespace std;
using namespace cv;
using namespace emscripten;

namespace pi {
    void AutosvgWASM::loadImage(uintptr_t buffer, int rows, int cols) {
        try {
            imagePixels = reinterpret_cast<unsigned int *>(buffer);
            img = new cv::Mat(rows, cols, CV_8UC4, imagePixels);
            cv::cvtColor(*img, *img, COLOR_RGBA2RGB);
        } catch (const char *message) {
            cout << "Error in loading image : %s" << message << endl;
        }
    }

    Pixel AutosvgWASM::getContourColor(const Contour &contour) {
        auto orig = new cv::Mat(img->rows, img->cols, CV_8UC4, imagePixels);
        cv::cvtColor(*orig, *orig, COLOR_RGBA2RGB);
        return Operations::findContourAvgColor(*orig, contour);
    }

    string AutosvgWASM::convertToSvg(int kColors, int sharpness) {
        SegmentedEdgeResult result = Operations::findColorSegmentedEdge(img, img, kColors);

        const vector<Pixel> dominantColors = result.colors;
        const vector<Contour> edges = result.edges;

        vector<Pixel> colors;
        for (auto contour: edges) {
            colors.push_back(this->getContourColor(contour));
        }
        vector<Curve> curves = CurveUtils::convertContoursToBezierCurves(
                edges,
                sharpness,
                colors
        );
        const vector<SVGParam> params = {
                {"width",  to_string(img->cols).c_str()},
                {"height", to_string(img->rows).c_str()},
                {"xmlns",  "http://www.w3.org/2000/svg"}
        };
        string svg = CurveUtils::createSvgFromBezierCurves(curves, params);
        cv::cvtColor(*img, *img, COLOR_RGB2RGBA);
        memcpy(imagePixels, img->data, img->rows * img->cols * sizeof(int));
        return svg;
    }
}