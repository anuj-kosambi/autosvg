import React, {FormEvent} from "react";
import cx from "classnames";
import {Button, ButtonGroup, Card, Classes, Elevation, FileInput, Label, Slider} from "@blueprintjs/core";

import s from "./App.module.scss";

function downloadBlobUrl(blobUrl: string, downloadFileName: string) {
    const a = document.createElement('a');
    a.setAttribute('download', downloadFileName);
    a.setAttribute('href', blobUrl);
    a.click();
}

function convertImageToSvg(canvas: HTMLCanvasElement, kColors: number, sharpness: number) {
    const ctx = canvas.getContext("2d");
    if (ctx == null) {
        return;
    }
    //@ts-ignore
    const _Module = Module;
    const AutosvgWASM = _Module.AutosvgWASM;

    const inst = new AutosvgWASM();

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const imageDataBuffer = imageData.data.buffer;
    const rows = canvas.height;
    const cols = canvas.width;
    const byteCounts = imageDataBuffer.byteLength;
    const dataPtr = _Module._malloc(byteCounts);
    const dataOnHeap = new Uint8ClampedArray(
        _Module.HEAPU8.buffer,
        dataPtr,
        byteCounts
    );
    dataOnHeap.set(imageData.data);

    inst.loadImage(dataOnHeap.byteOffset, rows, cols);

    const svg = inst.convertToSvg(kColors, sharpness);
    const blob = new Blob([svg], {
        type: 'image/svg+xml'
    });
    const blobUrl = URL.createObjectURL(blob);
    console.log(blobUrl);
    _Module._free(dataPtr);
    return blobUrl;
}

function App() {
    const [image, changeImage] = React.useState();
    const [svgBlob, changeBlobUrl] = React.useState();
    const [kColor, handleKColorChange] = React.useState(2);
    const [sharpness, handleSharpnessChange] = React.useState(5);
    const [memCanvas] = React.useState(document.createElement("canvas"));
    const [currentFileName, changeCurrentFileName] = React.useState();
    const [downloadFileName, changeDownloadFileName] = React.useState('output.svg');

    async function onFileChange(event: FormEvent<HTMLInputElement>) {
        // @ts-ignore
        const [file] = event.target.files;
        await handleFileUpload(file);
    }

    async function handleFileUpload(file: any) {
        const fileName = file.name.split('.')[0];
        const canvas = memCanvas;
        const imageURL = URL.createObjectURL(file);
        const dummyImg = new Image();
        const ctx = canvas.getContext("2d");
        if (ctx == null) {
            return;
        }

        await new Promise((resolve) => {
            dummyImg.onload = () => {
                const widthHeightRatio = dummyImg.width * 1.0 / dummyImg.height;
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
        const blobUrl = convertImageToSvg(memCanvas, kColor, sharpness);
        changeBlobUrl(blobUrl);
        changeDownloadFileName(`${currentFileName}.svg`);
    }

    function handleDownload() {
        downloadBlobUrl(svgBlob, downloadFileName);
    }

    function handleDrop(ev: React.DragEvent<HTMLDivElement>) {
      console.log('File(s) dropped');

      // Prevent default behavior (Prevent file from being opened)
      ev.preventDefault();
      ev.stopPropagation();

      if (ev.dataTransfer.items) {
        // Use DataTransferItemList interface to access the file(s)
        for (let i = 0; i < ev.dataTransfer.items.length; i++) {
          // If dropped items aren't files, reject them
          if (ev.dataTransfer.items[i].kind === 'file') {
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
       console.log('File(s) in drop zone'); 
      // Prevent default behavior (Prevent file from being opened)
      ev.preventDefault();
    }

    return (
        <div className={cx(Classes.DARK, "container", s.mainContainer)}>
            <div className="row container">
                <Card
                    elevation={Elevation.TWO}
                    className={cx("col-6", s.card)}
                   >
                    <h6>Input Image</h6>
                    <img src={image} className={cx(s.image)}/>
                </Card>
                <Card
                    elevation={Elevation.TWO}
                    className={cx("col-6", s.card)}
                >
                    <h6>Output Image</h6>
                    <img src={svgBlob} className={cx(s.image)}/>
                </Card>
            </div>
            <div className="padding-1rme row container">
                <div className="col-6-l col-12">
                    <h4>Settings</h4>
                    <div className="padding-top-1-5rem padding-bottom-1-5rem">
                        <Label>
                            Details
                        </Label>
                        <Slider
                            min={2}
                            max={6}
                            stepSize={1}
                            labelStepSize={1}
                            onChange={handleKColorChange}
                            value={kColor}
                        />
                        <Label>
                            Smoothness
                        </Label>
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
                <div className={cx("padding-1rem", "col-6-l","col-12")}
                style={{display:"flex", alignItems: "center", border: "2px dashed", borderRadius: "10px"}}
                onDrop={handleDrop} onDragOver={handleDragOver}
                >
                    <div>
                        <h6>Drop your .png or .jpg file here!</h6>
                        <ButtonGroup fill={true}>
                            <FileInput text="Choose file..." onInputChange={onFileChange}/>
                            <Button icon="tick-circle" onClick={handleConvert}>Convert</Button>
                            <Button icon="download" onClick={handleDownload}>Download</Button>
                        </ButtonGroup>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default App;
