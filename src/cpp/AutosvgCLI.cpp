//
// Created by Anuj Kosambi on 2/06/20.
//


#include <iostream>
#include <string>
#include <opencv2/opencv.hpp>
#include <cxxopts.hpp>

using namespace std;


int main(int argc, char **argv) {
  cxxopts::Options options("autosvg", "Tracing tool which can convert any jpg or png into svg");

  options.add_options()
    ("i,input", "Input Filename", cxxopts::value<std::string>())
    ("o,output", "Output Filename", cxxopts::value<std::string>())
    ("h,help", "Print Usage");


  try {

    auto result = options.parse(argc, argv);
    if (result.count("help")){
        std::cout << options.help() << std::endl;
        exit(0);
    }

    cout<<result["input"].as<std::string>()<<" "<<result["output"].as<std::string>();

  } catch(std::exception e) {
      std::cout << options.help() << std::endl;
      exit(0);
  }
  return 0;
}


