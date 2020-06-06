import React, { FormEvent } from "react";
import cx from "classnames";
import {
  Button,
  ButtonGroup,
  Card,
  Classes,
  Elevation,
  FileInput,
  Label,
  Slider,
  Spinner
} from "@blueprintjs/core";

import Editor from "./components/Editor";
import s from "./App.module.scss";
import _ from "lodash";
import { SVGJSONType } from "./components/Editor/Editor";

const autosvgWasmWorker = new Worker('./autosvg-wasm-worker.js');

function downloadBlobUrl(blobUrl: string, downloadFileName: string) {
  const a = document.createElement("a");
  a.setAttribute("download", downloadFileName);
  a.setAttribute("href", blobUrl);
  a.click();
}

function convertToJSONPath(path: SVGPathElement, index: any) {
  const d = _.reject(path.getAttribute("d")!.split(/\s+|,/), _.isEmpty);
  const startXy = _.take(d, 3);
  const { value, partition } = d.splice(3).reduce(
    // @ts-ignore
    (accum, item) => {
      if (_.isFinite(+item)) {
        return { value: accum.value, partition: [...accum.partition, item] };
      }
      return {
        value: [...accum.value, accum.partition],
        partition: [],
      };
    },
    { value: [], partition: [] }
  );
  console.log(value, partition);
  const objects = [...value, partition].reduce((accum, item) => {
    switch (item.length) {
      case 2: {
        return [
          ...accum,
          {
            x1: +item[0],
            y1: +item[1],
            x2: +item[0],
            y2: +item[1],
            x: +item[0],
            y: +item[1],
          },
        ];
      }
      case 6:
        return [
          ...accum,
          {
            x1: +item[0],
            y1: +item[1],
            x2: +item[2],
            y2: +item[3],
            x: +item[4],
            y: +item[5],
          },
        ];
      default:
        return accum;
    }
  }, []);
  return {
    moveX: +startXy[1],
    moveY: +startXy[2],
    x: +startXy[1],
    y: +startXy[2],
    path: objects,
    rotate: 0,
    stroke: path.getAttribute("fill") as string,
    strokeWidth: 1,
    type: "polygon",
    fill: path.getAttribute("fill"),
    closed: true,
  };
}
function convertToJSON(svgContent: string) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(svgContent, "text/xml");
  const svgEl: SVGAElement = doc.querySelector<SVGAElement>("svg")!;
  const path = doc.querySelectorAll("path");
  return {
    width: +svgEl.getAttribute("width")!,
    height: +svgEl.getAttribute("height")!,
    // @ts-ignore
    objects: Array.from(path.values()).map(convertToJSONPath),
  };
}

function convertImageToSvg(
  canvas: HTMLCanvasElement,
  kColors: number,
  sharpness: number
) {
    return new Promise<any>((resolve, reject) => {
        
        const ctx = canvas.getContext("2d");
        if (ctx == null) {
            reject('Error loading canvas');
            return;
        }
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

        autosvgWasmWorker.postMessage([imageData, kColors, sharpness]);

        // @ts-ignore
        autosvgWasmWorker.addEventListener('message', function(e) {
            resolve(e.data);
        });
    });
}

function App() {


  const [image, changeImage] = React.useState();
  const [svgBlob, changeBlobUrl] = React.useState();
  const [kColor, handleKColorChange] = React.useState(2);
  const [sharpness, handleSharpnessChange] = React.useState(5);
  const [memCanvas] = React.useState(document.createElement("canvas"));
  const [svgContent, changeSvgContent] = React.useState<SVGJSONType | null>(
    null
  );
  const [currentFileName, changeCurrentFileName] = React.useState();
  const [downloadFileName, changeDownloadFileName] = React.useState(
    "output.svg"
  );
  const [isOutputSpinnerVisible, changeOutputSpinnerVisibility] = React.useState(false);

  async function onFileChange(event: FormEvent<HTMLInputElement>) {
    // @ts-ignore
    const [file] = event.target.files;
    await handleFileUpload(file);
  }

  async function handleFileUpload(file: any) {
    const fileName = file.name.split(".")[0];
    const canvas = memCanvas;
    const imageURL = URL.createObjectURL(file);
    const dummyImg = new Image();
    const ctx = canvas.getContext("2d");
    if (ctx == null) {
      return;
    }

    await new Promise((resolve) => {
      dummyImg.onload = () => {
        const widthHeightRatio = (dummyImg.width * 1.0) / dummyImg.height;
        canvas.width = 600.0 * widthHeightRatio;
        canvas.height = 600.0;
        ctx.drawImage(dummyImg, 0, 0, canvas.width, canvas.height);
        resolve();
      };
      dummyImg.src = imageURL;
    });
    changeImage(imageURL);
    changeCurrentFileName(fileName);
  }

  function handleConvert() {
    changeOutputSpinnerVisibility(true);
    convertImageToSvg(memCanvas, kColor, sharpness)
    .then(result => {
        changeOutputSpinnerVisibility(false);
        if (!result) {
          return;
        }
        changeBlobUrl(result.blobUrl);
        changeSvgContent(convertToJSON(result.svg));
        changeDownloadFileName(`${currentFileName}.svg`);
    })
    .catch(error => {
        changeOutputSpinnerVisibility(false);
    });
  }

  function handleDownload() {
    downloadBlobUrl(svgBlob, downloadFileName);
  }

  function handleDrop(ev: React.DragEvent<HTMLDivElement>) {
    console.log("File(s) dropped");

    // Prevent default behavior (Prevent file from being opened)
    ev.preventDefault();
    ev.stopPropagation();

    if (ev.dataTransfer.items) {
      // Use DataTransferItemList interface to access the file(s)
      for (let i = 0; i < ev.dataTransfer.items.length; i++) {
        // If dropped items aren't files, reject them
        if (ev.dataTransfer.items[i].kind === "file") {
          const file = ev.dataTransfer.items[i].getAsFile();
          if (file !== null) {
            handleFileUpload(file);
            break;
          }
        }
      }
    } else {
      // Use DataTransfer interface to access the file(s)
      for (var i = 0; i < ev.dataTransfer.files.length; i++) {
        handleFileUpload(ev.dataTransfer.files[i]);
        break;
      }
    }
  }

  function handleDragOver(ev: React.DragEvent<HTMLDivElement>) {
    console.log("File(s) in drop zone");
    // Prevent default behavior (Prevent file from being opened)
    ev.preventDefault();
  }

  return (
    <div className={cx(Classes.DARK, s.mainContainer)}>
      <div className="row">
        <Card elevation={Elevation.TWO} className={cx("col-4", s.card)}>
          <h6>Input Image</h6>
          <img src={image} className={cx(s.image)} />
        </Card>
        <Card elevation={Elevation.TWO} className={cx("col-8", s.card)}>
          <div className={s.loaderWrapper}
              style={{display: isOutputSpinnerVisible? 'block': 'none'}}>
              <Spinner size={100} />
          </div>
          <div style={{display: !isOutputSpinnerVisible? 'block': 'none'}}>
          <Editor data={svgContent} />
          </div>
        </Card>
      </div>
      <div className="padding-1rem row">
        <div className="col-6-l col-12">
          <h4>Settings</h4>
          <div className="padding-top-1-5rem padding-bottom-1-5rem">
            <Label>Details</Label>
            <Slider
              min={2}
              max={16}
              stepSize={1}
              labelStepSize={1}
              onChange={handleKColorChange}
              value={kColor}
            />
            <Label>Smoothness</Label>
            <Slider
              min={1}
              max={20}
              stepSize={1}
              labelStepSize={1}
              onChange={handleSharpnessChange}
              value={sharpness}
            />
          </div>
        </div>
        <div
          className={cx("padding-1rem", "col-6-l", "col-12")}
          style={{
            display: "flex",
            alignItems: "center",
            border: "2px dashed",
            borderRadius: "10px",
          }}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        >
          <div>
            <h6>Drop your .png or .jpg file here!</h6>
            <ButtonGroup fill={true}>
              <FileInput text="Choose file..." onInputChange={onFileChange} />
              <Button icon="tick-circle" onClick={handleConvert}>
                Convert
              </Button>
              <Button icon="download" onClick={handleDownload}>
                Download
              </Button>
            </ButtonGroup>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
