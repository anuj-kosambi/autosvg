import React, {FormEvent} from "react";
import cx from "classnames";
import {Card, Classes, Elevation, FileInput} from "@blueprintjs/core";

import s from "./App.module.scss";

function cleanString(input: string) {
    let output = "";
    for (let i = 0; i < input.length; i++) {
        if (input.charCodeAt(i) <= 127 || input.charCodeAt(i) >= 160 && input.charCodeAt(i) <= 255) {
            output += input.charAt(i);
        }
    }
    return output;
}

function App() {
    const [image, changeImage] = React.useState();

    async function onFileChange(event: FormEvent<HTMLInputElement>) {
        // @ts-ignore
        const [file] = event.target.files;
        const imageURL = URL.createObjectURL(file);
        // @ts-ignore
        const _Module = Module;
        const AutosvgWASM = _Module.AutosvgWASM;
        const inst = new AutosvgWASM();

        const canvas: HTMLCanvasElement = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        if (ctx == null) {
            return;
        }

        const dummyImg = new Image();

        await new Promise((resolve) => {
            dummyImg.onload = () => {
                canvas.width = dummyImg.width;
                canvas.height = dummyImg.height;
                ctx.drawImage(dummyImg, 0, 0);
                resolve();
            };
            dummyImg.src = imageURL;
        });
        changeImage(imageURL);

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

        const svg = inst.convertToSvg();
        console.log(svg);
        const blob = new Blob([cleanString(svg)], {
            type: 'image/svg+xml'
        });
        const blobUrl = URL.createObjectURL(blob);
        console.log(blobUrl);
        // @ts-ignore
        const outputCanvas: HTMLCanvasElement | null = document.getElementById(
            "canvasOutput"
        );
        if (!outputCanvas) {
            return;
        }
        outputCanvas.height = canvas.height;
        outputCanvas.width = canvas.width;
        /*
        // @ts-ignore
        outputCanvas.getContext("2d").putImageData(
            new ImageData(dataOnHeap, canvas.width, canvas.height),
            0,
            0
        );*/
        const output = new Image();

        await new Promise((resolve) => {
            output.onload = () => {
                // @ts-ignore
                outputCanvas.getContext("2d").drawImage(output, 0, 0);
                URL.revokeObjectURL(blobUrl);
                resolve();
            };
            output.src = blobUrl;
        });
        _Module._free(dataPtr);
    }

    return (
        <div className={cx(Classes.DARK, "container", s.mainContainer)}>
            <div className="row container">
                <Card
                    interactive={true}
                    elevation={Elevation.TWO}
                    className={cx("col-6", s.card)}
                >
                    <h6>Input Image</h6>
                    <img src={image} className={cx(s.image)}/>
                </Card>
                <Card
                    interactive={true}
                    elevation={Elevation.TWO}
                    className={cx("col-6", s.card)}
                >
                    <h6>Output Image</h6>
                    <canvas id="canvasOutput" className={s.image}/>
                </Card>
            </div>
            <FileInput text="Choose file..." onInputChange={onFileChange}/>
        </div>
    );
}

export default App;
