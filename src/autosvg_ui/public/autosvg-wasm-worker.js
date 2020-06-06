self.importScripts('./autosvg-wasm.js');
onmessage = function(e) {
    console.log('Message received from main script');

    const _Module = Module;
    const AutosvgWASM = _Module.AutosvgWASM;

    const inst = new AutosvgWASM();

    const [imageData, kColors, sharpness] = e.data;
    const imageDataBuffer = imageData.data.buffer;
    const rows = imageData.height;
    const cols = imageData.width;
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
        type: "image/svg+xml",
    });

    const blobUrl = URL.createObjectURL(blob);
    _Module._free(dataPtr);
    postMessage({ blobUrl, svg });
}