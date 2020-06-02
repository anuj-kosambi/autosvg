//
// Created by Anuj Kosambi on 2/06/20.
//


#include <iostream>
#include <string>
#include <opencv2/opencv.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/highgui.hpp>
#include <cxxopts.hpp>
#include "AutosvgCLI.hpp"
#include <fstream>

using namespace std;
using namespace cv;

namespace pi {
      Pixel AutosvgCLI::getContourColor(const Contour &contour) {
          cv::Mat image = cv::imread(this->inputFileName, IMREAD_COLOR);
          return Operations::findContourAvgColor(image, contour);
      }

      string AutosvgCLI::convertToSvg(int kColors, int sharpness) {
        cv::Mat image;
        image = cv::imread(this->inputFileName, IMREAD_COLOR);
        auto img = new cv::Mat;
        *img = image;
        
        auto ratio = img->rows/(img->cols * 1.0);
        resize(*img, *img, cv::Size(600,600 * ratio), 0, 0);

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
        return svg;

      }

      void AutosvgCLI::writeImage(const string fileName, const string svgContent) {
        ofstream file;
        file.open (fileName);
        file << svgContent;
        file.close();
      }
}


int main(int argc, char **argv) {
  cxxopts::Options options("autosvg", "Tracing tool which can convert any jpg or png into svg");

  options.add_options()
    ("i,input", "Input Filename", cxxopts::value<std::string>())
    ("o,output", "Output Filename", cxxopts::value<std::string>()->default_value("out.svg"))
    ("k,colors", "Color Details", cxxopts::value<int>()->default_value("3"))
    ("s,smoothness", "Smoothness Index", cxxopts::value<int>()->default_value("5"))
    ("h,help", "Print Usage");

  try {

    auto result = options.parse(argc, argv);

    if (result.count("help")){
        std::cout << options.help() << std::endl;
        exit(0);
    }

    pi::AutosvgCLI inst;
    inst.inputFileName = result["input"].as<std::string>();
    inst.outputFileName = result["output"].as<std::string>();

    
    auto svgContent = inst.convertToSvg(result["colors"].as<int>(), result["smoothness"].as<int>());  
    inst.writeImage(inst.outputFileName, svgContent);

  } catch(const std::exception& e) {
    std::cout << options.help() << std::endl;
    exit(0);
  }
  return 0;
}


