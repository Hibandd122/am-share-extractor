/**
 * AM Auto Lyrics - Ultra-Fast Transient & Spectral Flux Beat Detection Engine
 */

class AMAudioEngine {
    constructor() {
        this.ctx = null;
        this.audioBuffer = null;
        this.sourceNode = null;
        this.isPlaying = false;
        this.startTime = 0;
        this.pauseOffset = 0;
        this.duration = 0;

        this.detectedBeats = []; // Array of timestamps in ms
        this.detectedBpm = 120;
        this.tappedBeats = [];

        // Default natural timing offset
        this.latencyOffsetMs = 0;
        this.sensitivity = 1.35; // Balanced natural sensitivity

        this.onPlaybackUpdate = null;
        this.onPlaybackEnded = null;
    }

    _initContext() {
        if (!this.ctx) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            this.ctx = new AudioCtx();
        }
        if (this.ctx.state === "suspended") {
            this.ctx.resume();
        }
    }

    /**
     * Loads and decodes an audio file
     */
    async loadAudio(fileOrBuffer) {
        this._initContext();
        let arrayBuffer;
        if (fileOrBuffer instanceof ArrayBuffer) {
            arrayBuffer = fileOrBuffer;
        } else {
            arrayBuffer = await fileOrBuffer.arrayBuffer();
        }

        this.audioBuffer = await this.ctx.decodeAudioData(arrayBuffer);
        this.duration = this.audioBuffer.duration;
        this.pauseOffset = 0;
        this.isPlaying = false;
        this.tappedBeats = [];

        // Run ultra-fast transient attack detection
        this.detectBeats();
        return {
            duration: this.duration,
            durationMs: Math.round(this.duration * 1000),
            bpm: this.detectedBpm,
            beatsCount: this.detectedBeats.length
        };
    }

    /**
     * High-Precision Spectral Flux & Rising-Edge Attack Detector
     * Catches the exact 0ms instant when drums/vocals hit, eliminating lag.
     */
    detectBeats(sensitivity = null, offsetMs = null) {
        if (!this.audioBuffer) return;

        if (sensitivity !== null) this.sensitivity = sensitivity;
        if (offsetMs !== null) this.latencyOffsetMs = offsetMs;

        const rawData = this.audioBuffer.getChannelData(0);
        const sampleRate = this.audioBuffer.sampleRate;
        
        // Window of 512 samples (~11.6ms at 44.1kHz for ultra-sharp transient accuracy)
        const frameSize = 512;
        const totalFrames = Math.floor(rawData.length / frameSize);
        const frameEnergy = new Float32Array(totalFrames);
        const spectralFlux = new Float32Array(totalFrames);

        // 1. Calculate RMS energy per 11.6ms frame
        for (let i = 0; i < totalFrames; i++) {
            let sum = 0;
            const start = i * frameSize;
            for (let j = 0; j < frameSize; j++) {
                const val = rawData[start + j];
                sum += val * val;
            }
            frameEnergy[i] = Math.sqrt(sum / frameSize);
        }

        // 2. Calculate Spectral Flux (First Derivative of Rising Attack)
        for (let i = 1; i < totalFrames; i++) {
            const diff = frameEnergy[i] - frameEnergy[i - 1];
            spectralFlux[i] = diff > 0 ? diff : 0; // Half-wave rectification
        }

        // 3. Dynamic adaptive threshold with balanced window
        const localWindow = 20;
        const detected = [];
        const minBeatDistanceMs = 360; // Natural phrase & beat cadence (~160 BPM max)
        let lastBeatTimeMs = -minBeatDistanceMs;

        for (let i = localWindow; i < totalFrames - localWindow; i++) {
            let localSum = 0;
            for (let w = -localWindow; w <= localWindow; w++) {
                localSum += spectralFlux[i + w];
            }
            const localMean = localSum / (2 * localWindow + 1);
            const threshold = localMean * this.sensitivity + 0.005;

            // Check if current frame is a local peak and exceeds threshold
            if (
                spectralFlux[i] > threshold &&
                spectralFlux[i] > spectralFlux[i - 1] &&
                spectralFlux[i] >= spectralFlux[i + 1]
            ) {
                const exactTimeMs = (i * frameSize / sampleRate) * 1000;
                
                if (exactTimeMs - lastBeatTimeMs >= minBeatDistanceMs) {
                    // Apply pre-roll latency compensation so animation starts instantly
                    const compensatedTimeMs = Math.max(0, Math.round(exactTimeMs + this.latencyOffsetMs));
                    detected.push(compensatedTimeMs);
                    lastBeatTimeMs = exactTimeMs;
                }
            }
        }

        this.detectedBeats = detected;

        // Estimate BPM from peak intervals
        if (detected.length >= 2) {
            const intervals = [];
            for (let i = 1; i < detected.length; i++) {
                const diff = detected[i] - detected[i - 1];
                if (diff >= 250 && diff <= 1400) {
                    intervals.push(diff);
                }
            }
            if (intervals.length > 0) {
                intervals.sort((a, b) => a - b);
                const medianInterval = intervals[Math.floor(intervals.length / 2)];
                this.detectedBpm = Math.round((60000 / medianInterval) * 10) / 10;
            }
        }
    }

    /**
     * Intelligent Voice Activity Detection (VAD) & Phrase Segmenter
     * Segments sung vocal sentences based on energy envelope and silence pauses.
     */
    detectVocalPhrases(targetCount = 0) {
        if (!this.audioBuffer) return [];

        const rawData = this.audioBuffer.getChannelData(0);
        const sampleRate = this.audioBuffer.sampleRate;
        const windowSize = Math.floor(sampleRate * 0.05); // 50ms window
        const totalWindows = Math.floor(rawData.length / windowSize);
        const rms = new Float32Array(totalWindows);

        let maxRms = 0;
        for (let i = 0; i < totalWindows; i++) {
            let sum = 0;
            const start = i * windowSize;
            for (let j = 0; j < windowSize; j++) {
                const s = rawData[start + j];
                sum += s * s;
            }
            rms[i] = Math.sqrt(sum / windowSize);
            if (rms[i] > maxRms) maxRms = rms[i];
        }

        if (maxRms === 0) return [];

        // Moving average smoothing (~300ms window)
        const smooth = new Float32Array(totalWindows);
        const half = 3;
        for (let i = 0; i < totalWindows; i++) {
            let sum = 0, count = 0;
            for (let k = -half; k <= half; k++) {
                const idx = i + k;
                if (idx >= 0 && idx < totalWindows) {
                    sum += rms[idx];
                    count++;
                }
            }
            smooth[i] = sum / count;
        }

        const threshold = maxRms * 0.14; // 14% of peak energy
        const segments = [];
        let inSeg = false;
        let startMs = 0;
        let silenceCountMs = 0;

        for (let i = 0; i < totalWindows; i++) {
            const timeMs = Math.round(i * 50);
            if (smooth[i] >= threshold) {
                if (!inSeg) {
                    inSeg = true;
                    startMs = Math.max(0, timeMs - 50);
                }
                silenceCountMs = 0;
            } else {
                if (inSeg) {
                    silenceCountMs += 50;
                    if (silenceCountMs >= 450) { // 450ms silence marks phrase end
                        const endMs = timeMs - silenceCountMs;
                        if (endMs - startMs >= 1100) {
                            segments.push({ start_ms: startMs, end_ms: endMs });
                        }
                        inSeg = false;
                        silenceCountMs = 0;
                    }
                }
            }
        }

        if (inSeg) {
            const endMs = Math.round(totalWindows * 50);
            if (endMs - startMs >= 1100) {
                segments.push({ start_ms: startMs, end_ms: endMs });
            }
        }

        return segments;
    }

    /**
     * Playback Controls
     */
    play(offsetSeconds = null) {
        if (!this.audioBuffer) return;
        this._initContext();

        if (this.isPlaying) {
            this.pause();
        }

        const offset = offsetSeconds !== null ? offsetSeconds : this.pauseOffset;
        if (offset >= this.duration) {
            this.pauseOffset = 0;
        }

        this.sourceNode = this.ctx.createBufferSource();
        this.sourceNode.buffer = this.audioBuffer;
        this.sourceNode.connect(this.ctx.destination);

        this.sourceNode.onended = () => {
            if (this.isPlaying && this.getCurrentTime() >= this.duration - 0.1) {
                this.isPlaying = false;
                this.pauseOffset = 0;
                if (this.onPlaybackEnded) this.onPlaybackEnded();
            }
        };

        const safeOffset = Math.max(0, Math.min(this.duration, offset));
        this.sourceNode.start(0, safeOffset);
        this.startTime = this.ctx.currentTime - safeOffset;
        this.isPlaying = true;

        this._trackProgress();
    }

    pause() {
        if (!this.isPlaying) return;
        if (this.sourceNode) {
            try { this.sourceNode.stop(); } catch(e) {}
            this.sourceNode.disconnect();
            this.sourceNode = null;
        }
        this.pauseOffset = this.getCurrentTime();
        this.isPlaying = false;
    }

    seek(seconds) {
        const safe = Math.max(0, Math.min(this.duration, seconds));
        this.pauseOffset = safe;
        if (this.isPlaying) {
            this.play(safe);
        } else if (this.onPlaybackUpdate) {
            this.onPlaybackUpdate(safe);
        }
    }

    getCurrentTime() {
        if (!this.isPlaying || !this.ctx) return this.pauseOffset;
        return Math.min(this.duration, Math.max(0, this.ctx.currentTime - this.startTime));
    }

    _trackProgress() {
        if (!this.isPlaying) return;
        const cur = this.getCurrentTime();
        if (this.onPlaybackUpdate) this.onPlaybackUpdate(cur);
        requestAnimationFrame(() => this._trackProgress());
    }

    /**
     * Manual Tap to Beat recorder with human latency compensation
     */
    tapBeat() {
        const rawMs = Math.round(this.getCurrentTime() * 1000);
        // Human reaction time offset: compensate by ~120ms
        const compensatedMs = Math.max(0, rawMs - 120);
        this.tappedBeats.push(compensatedMs);
        this.tappedBeats.sort((a, b) => a - b);
        return compensatedMs;
    }
}
