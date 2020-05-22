//
// Created by Anuj Kosambi on 21/05/20.
//

#ifndef AUTOSVG_WASM_CURVEUTILS_HPP
#define AUTOSVG_WASM_CURVEUTILS_HPP

#include <iostream>

using namespace std;

#include <string>
#include <utils/Constants.hpp>

namespace pi {

    class CurveUtils {
    public:
        static vector<Curve> convertContoursToBezierCurves(const vector<Contour> &contours);

        static string createSvgFromBezierCurves(const vector<Curve> &curves, const vector<Pixel> &colors,
                                                const vector<SVGParam> &params);

    private:
        static string convertCurveIntoSvgPathData(const Curve &curves);

        static Curve fitContourToCurve(const Contour &contour);

        static CurveSegment fitPointsToCurveSegment(const Contour &contourPart);
    };

}

#endif //AUTOSVG_WASM_CURVEUTILS_HPP
