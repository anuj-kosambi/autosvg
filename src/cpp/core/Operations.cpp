//
// Created by Anuj Kosambi on 20/05/20.
//

#include <opencv2/core.hpp>
#include <opencv2/opencv.hpp>
#include <utils/underscore.hpp>
#include <NumCpp.hpp>

#include "Operations.hpp"

using namespace std;

namespace pi {
    cv::Mat Operations::kMeanSegmentation(cv::Mat *src, cv::Mat *out, unsigned int k) {
        cv::Mat data = src->reshape(1, src->rows * src->cols);
        data.convertTo(data, CV_32F);
        std::vector<int> labels;
        cv::Mat1f colors;

        cv::kmeans(data,
                   k,
                   labels,
                   cv::TermCriteria(cv::TermCriteria::EPS + cv::TermCriteria::MAX_ITER, 100, 1),
                   10,
                   cv::KMEANS_PP_CENTERS,
                   colors);
        for (unsigned int i = 0; i < src->rows * src->cols; i++) {
            data.at<float>(i, 0) = colors(labels[i], 0);
            data.at<float>(i, 1) = colors(labels[i], 1);
            data.at<float>(i, 2) = colors(labels[i], 2);
        }

        cv::Mat outputImage = data.reshape(3, src->rows);
        outputImage.convertTo(outputImage, CV_8U);
        *out = outputImage;
        return colors.reshape(3, k);
    }

    void Operations::sharpen(cv::Mat *src, cv::Mat *out, unsigned int k) {
        cv::Mat blur;
        cv::GaussianBlur(*src, blur, cv::Size(k, k), 3);
        cv::addWeighted(*src, 1.5, blur, -0.5, 0, *out);
    }

    SegmentedEdgeResult Operations::findColorSegmentedEdge(cv::Mat *src, cv::Mat *out, unsigned int k) {
        auto *kMean = new cv::Mat;

        cv::Mat edge(src->rows, src->cols, CV_8UC1, cv::Scalar(0, 0, 0));

        auto *edges = new vector<Contour>();
        auto *result = new SegmentedEdgeResult;

        auto colors = Operations::kMeanSegmentation(src, kMean, k);
        colors.forEach<Pixel>([kMean, edges](Pixel &pixel, const int *position) -> void {
                                  cv::Mat mask;
                                  const auto imageArea = kMean->rows * kMean->cols;
                                  const auto &color = cv::Scalar(pixel.x, pixel.y, pixel.z);
                                  cv::inRange(*kMean, color, color,
                                              mask);
                                  vector<Contour> contours;
                                  vector<Hierarchy> hierarchy;

                                  cv::findContours(mask, contours, hierarchy, cv::RETR_TREE, cv::CHAIN_APPROX_NONE);
                                  contours = underscore::filter<vector<Contour>>(contours, [imageArea](Contour contour) -> bool {
                                      auto area = cv::contourArea(contour);
                                      return area > MINIMUM_CONTOUR_AREA &&
                                             area < imageArea * MAXIMUM_CONTOUR_TO_IMAGE_RATIO;
                                  });
                                  edges->insert(edges->end(), contours.begin(), contours.end());
                                  return;
                              }
        );

        result->colors = colors;

        result->edges = *edges;

        cv::drawContours(edge, *edges, -1, cv::Scalar(255));
        cv::cvtColor(edge, edge, cv::COLOR_GRAY2RGB);
        *out = edge;

        return *result;
    }

    std::vector<Pixel> Operations::findContourAvgColor(const cv::Mat &src, const std::vector<Contour> &contours) {

        return underscore::map<std::vector<Pixel>>(contours, [&src](Contour contour) -> Pixel {
            cv::Mat mask(src.rows, src.cols, CV_8UC1, cv::Scalar(0, 0, 0));
            auto *edges = new vector<Contour>();
            edges->push_back(contour);
            cv::drawContours(mask, *edges, -1, cv::Scalar(255), -1);
            cv::Scalar color = cv::mean(src, mask = mask);
            return {float(color[0]), float(color[1]), float(color[2])};
        });
    }
}