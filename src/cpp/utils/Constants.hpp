//
// Created by Anuj Kosambi on 21/05/20.
//

#ifndef AUTOSVG_WASM_CONSTANTS_HPP
#define AUTOSVG_WASM_CONSTANTS_HPP

#include <vector>
#include <opencv2/opencv.hpp>

typedef cv::Point3_<float> Pixel;
typedef std::vector<cv::Point> Contour;
typedef cv::Vec4i Hierarchy;
typedef std::vector<cv::Point> CurveSegment;
typedef std::vector<CurveSegment> Curve;

struct SVGParam {
    const char *key;
    std::string value;
};

#define SHARPNESS 4
#define K_COLORS 3

struct SegmentedEdgeResult {
    std::vector<Contour> edges;
    std::vector<Pixel> colors;
};

#define MINIMUM_CONTOUR_AREA 36
#define MAXIMUM_CONTOUR_TO_IMAGE_RATIO 0.95


#endif //AUTOSVG_WASM_CONSTANTS_HPP
