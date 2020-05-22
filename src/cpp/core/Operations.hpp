//
// Created by Anuj Kosambi on 20/05/20.
//

#ifndef AUTOSVG_WASM_OPERATIONS_HPP
#define AUTOSVG_WASM_OPERATIONS_HPP


#include <opencv2/core/mat.hpp>
#include <utils/Constants.hpp>

namespace pi {


    class Operations {
    public:
        cv::Mat static kMeanSegmentation(cv::Mat *src, cv::Mat *out, unsigned int k);

        SegmentedEdgeResult static findColorSegmentedEdge(cv::Mat *src, cv::Mat *out, unsigned int k);

        void static sharpen(cv::Mat *src, cv::Mat *out, unsigned int k = 5);
    };

}


#endif //AUTOSVG_WASM_OPERATIONS_HPP
