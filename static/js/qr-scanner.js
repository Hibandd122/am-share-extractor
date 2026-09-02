/**
 * NEXUS ALIGHT EXTRACTOR - QR Code to XML Scanner Engine
 * Supports: Image file upload, Drag & Drop, Clipboard (Ctrl+V) paste, and Live Webcam scanning.
 */

class NexusQRScanner {
    constructor() {
        this.videoStream = null;
        this.isScanningCamera = false;
        this.canvas = document.createElement("canvas");
        this.ctx = this.canvas.getContext("2d", { willReadFrequently: true });
    }

    /**
     * Decodes QR code from an Image element or HTMLCanvasElement using jsQR
     */
    decodeFromImage(imageElement) {
        return new Promise((resolve, reject) => {
            if (typeof jsQR === "undefined") {
                reject(new Error("QR Scanner engine (jsQR) is not loaded."));
                return;
            }

            try {
                this.canvas.width = imageElement.naturalWidth || imageElement.width;
                this.canvas.height = imageElement.naturalHeight || imageElement.height;
                this.ctx.drawImage(imageElement, 0, 0, this.canvas.width, this.canvas.height);

                const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
                const code = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: "dontInvert",
                }) || jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: "attemptBoth",
                });

                if (code && code.data) {
                    resolve(code.data);
                } else {
                    reject(new Error("No readable QR code found in this image."));
                }
            } catch (err) {
                reject(err);
            }
        });
    }

    /**
     * Decodes QR code from a File or Blob object
     */
    decodeFromFile(file) {
        return new Promise((resolve, reject) => {
            if (!file.type.startsWith("image/")) {
                reject(new Error("Selected file is not an image."));
                return;
            }

            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = async () => {
                    try {
                        const result = await this.decodeFromImage(img);
                        resolve({ text: result, dataUrl: e.target.result });
                    } catch (err) {
                        reject(err);
                    }
                };
                img.onerror = () => reject(new Error("Failed to load image file."));
                img.src = e.target.result;
            };
            reader.onerror = () => reject(new Error("Failed to read file."));
            reader.readAsDataURL(file);
        });
    }

    /**
     * Starts live webcam stream scanning
     */
    async startCamera(videoElement, onScanCallback, onErrorCallback) {
        if (typeof jsQR === "undefined") {
            if (onErrorCallback) onErrorCallback(new Error("QR Scanner engine not loaded."));
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment" }
            });
            this.videoStream = stream;
            videoElement.srcObject = stream;
            videoElement.setAttribute("playsinline", true);
            await videoElement.play();

            this.isScanningCamera = true;
            this._scanCameraFrame(videoElement, onScanCallback);
        } catch (err) {
            if (onErrorCallback) onErrorCallback(err);
        }
    }

    _scanCameraFrame(videoElement, onScanCallback) {
        if (!this.isScanningCamera) return;

        if (videoElement.readyState === videoElement.HAVE_ENOUGH_DATA) {
            this.canvas.width = videoElement.videoWidth;
            this.canvas.height = videoElement.videoHeight;
            this.ctx.drawImage(videoElement, 0, 0, this.canvas.width, this.canvas.height);

            const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
            const code = jsQR(imageData.data, imageData.width, imageData.height, {
                inversionAttempts: "dontInvert",
            });

            if (code && code.data) {
                this.stopCamera();
                if (onScanCallback) onScanCallback(code.data);
                return;
            }
        }

        requestAnimationFrame(() => this._scanCameraFrame(videoElement, onScanCallback));
    }

    /**
     * Stops active webcam stream
     */
    stopCamera() {
        this.isScanningCamera = false;
        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => track.stop());
            this.videoStream = null;
        }
    }
}

// Global scanner instance
const qrScanner = new NexusQRScanner();

// Global clipboard image listener
window.addEventListener("paste", async (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf("image") !== -1) {
            const file = items[i].getAsFile();
            if (file) {
                if (typeof showToast === "function") {
                    showToast("Scanning pasted QR code image...", "info");
                }
                try {
                    const res = await qrScanner.decodeFromFile(file);
                    handleDecodedQR(res.text);
                } catch (err) {
                    if (typeof showToast === "function") {
                        showToast(err.message || "No QR code detected in pasted image.", "error");
                    }
                }
                break;
            }
        }
    }
});

function handleDecodedQR(text) {
    if (!text) return;
    const cleanText = text.trim();
    
    // Check if on home page with urlInput
    const input = document.getElementById("urlInput");
    if (input) {
        input.value = cleanText;
        if (typeof showToast === "function") {
            showToast("✓ QR Code decoded: " + cleanText, "success");
        }
        // If quick inspect button exists, click it or highlight
        const inspectBtn = document.getElementById("inspectBtn");
        if (inspectBtn) inspectBtn.click();
        return;
    }

    // If on QR dedicated page, update the UI
    const qrResultInput = document.getElementById("qrDecodedUrl");
    const qrResultCard = document.getElementById("qrResultCard");
    if (qrResultInput && qrResultCard) {
        qrResultInput.value = cleanText;
        qrResultCard.style.display = "block";
        qrResultCard.scrollIntoView({ behavior: "smooth" });
        if (typeof showToast === "function") {
            showToast("✓ QR Code scanned successfully!", "success");
        }
    }
}
