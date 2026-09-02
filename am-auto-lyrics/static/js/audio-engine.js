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
        this.beatConfidence = 0;
        this.detectedOnsets = [];
        this.tappedBeats = [];

        // Default natural timing offset
        this.latencyOffsetMs = -180;
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
            beatsCount: this.detectedBeats.length,
            confidence: Math.round(this.beatConfidence * 100)
        };
    }

    /**
     * Production beat detector:
     * mono mix -> Hann-window FFT -> multi-band spectral flux -> adaptive
     * threshold -> onset peaks -> tempo/phase tracking. The old detector
     * only compared two RMS values, which made it particularly vulnerable to
     * vocals and volume changes.
     */
    detectBeats(sensitivity = null, offsetMs = null) {
        if (!this.audioBuffer) return;

        if (sensitivity !== null) this.sensitivity = sensitivity;
        if (offsetMs !== null) this.latencyOffsetMs = offsetMs;

        const rawData = this._toMono(this.audioBuffer);
        const sampleRate = this.audioBuffer.sampleRate;
        const frameSize = 1024;
        const hopSize = 256;
        const fftSize = 1024;
        const frameCount = Math.max(0, Math.floor((rawData.length - frameSize) / hopSize) + 1);
        const flux = new Float32Array(frameCount);
        const previous = new Float32Array(fftSize / 2 + 1);
        const real = new Float32Array(fftSize);
        const imag = new Float32Array(fftSize);
        const window = this._hannWindow(fftSize);
        for (let frame = 0; frame < frameCount; frame++) {
            const start = frame * hopSize;
            real.fill(0); imag.fill(0);
            for (let j = 0; j < frameSize; j++) real[j] = rawData[start + j] * window[j];
            this._fft(real, imag);

            let value = 0;
            for (let bin = 1; bin <= fftSize / 2; bin++) {
                const magnitude = Math.sqrt(real[bin] * real[bin] + imag[bin] * imag[bin]);
                const hz = bin * sampleRate / fftSize;
                const bandWeight = hz < 180 ? 1.35 : (hz < 2500 ? 1.0 : 0.72);
                const rise = Math.max(0, magnitude - previous[bin]);
                value += rise * bandWeight;
                previous[bin] = magnitude;
            }
            flux[frame] = Math.log1p(value);
        }

        // Normalize and locally detrend the onset envelope.
        let maxFlux = 0;
        for (let i = 0; i < flux.length; i++) if (flux[i] > maxFlux) maxFlux = flux[i];
        if (maxFlux > 0) for (let i = 0; i < flux.length; i++) flux[i] /= maxFlux;

        const localWindow = Math.max(8, Math.round(0.35 * sampleRate / hopSize));
        const candidates = [];
        for (let i = localWindow; i < flux.length - localWindow; i++) {
            let sum = 0, sumSq = 0;
            for (let j = i - localWindow; j <= i + localWindow; j++) {
                sum += flux[j]; sumSq += flux[j] * flux[j];
            }
            const count = localWindow * 2 + 1;
            const mean = sum / count;
            const std = Math.sqrt(Math.max(0, sumSq / count - mean * mean));
            const threshold = mean + this.sensitivity * Math.max(std, 0.025);
            if (flux[i] >= threshold && flux[i] >= flux[i - 1] && flux[i] > flux[i + 1]) {
                const timeMs = i * hopSize / sampleRate * 1000;
                candidates.push({ timeMs, strength: flux[i] - mean });
            }
        }

        // Keep strong peaks first within a short refractory period, then sort.
        const minOnsetDistance = 110;
        candidates.sort((a, b) => b.strength - a.strength);
        const peaks = [];
        for (const candidate of candidates) {
            if (peaks.every(p => Math.abs(p.timeMs - candidate.timeMs) >= minOnsetDistance)) peaks.push(candidate);
        }
        peaks.sort((a, b) => a.timeMs - b.timeMs);
        this.detectedOnsets = peaks.map(p => Math.max(0, Math.round(p.timeMs + this.latencyOffsetMs)));

        const tempo = this._estimateTempo(peaks.map(p => p.timeMs));
        this.detectedBpm = tempo.bpm;
        this.beatConfidence = tempo.confidence;
        const grid = this._buildBeatGrid(peaks, tempo.bpm, tempo.phaseMs);
        this.detectedBeats = grid.map(ms => Math.max(0, Math.round(ms + this.latencyOffsetMs)));
    }

    _toMono(buffer) {
        const mono = new Float32Array(buffer.length);
        for (let c = 0; c < buffer.numberOfChannels; c++) {
            const channel = buffer.getChannelData(c);
            for (let i = 0; i < buffer.length; i++) mono[i] += channel[i] / buffer.numberOfChannels;
        }
        return mono;
    }

    _hannWindow(size) {
        const result = new Float32Array(size);
        for (let i = 0; i < size; i++) result[i] = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / size);
        return result;
    }

    _fft(real, imag) {
        const n = real.length;
        for (let i = 1, j = 0; i < n; i++) {
            let bit = n >> 1;
            for (; j & bit; bit >>= 1) j ^= bit;
            j ^= bit;
            if (i < j) { [real[i], real[j]] = [real[j], real[i]]; [imag[i], imag[j]] = [imag[j], imag[i]]; }
        }
        for (let size = 2; size <= n; size <<= 1) {
            const half = size >> 1, angle = -2 * Math.PI / size;
            for (let start = 0; start < n; start += size) {
                for (let k = 0; k < half; k++) {
                    const c = Math.cos(angle * k), s = Math.sin(angle * k);
                    const i = start + k, j = i + half;
                    const tr = real[j] * c - imag[j] * s, ti = real[j] * s + imag[j] * c;
                    real[j] = real[i] - tr; imag[j] = imag[i] - ti;
                    real[i] += tr; imag[i] += ti;
                }
            }
        }
    }

    _estimateTempo(times) {
        if (times.length < 2) return { bpm: 120, phaseMs: times[0] || 0, confidence: 0 };
        const scores = [];
        for (let bpm = 60; bpm <= 200; bpm += 0.5) {
            const interval = 60000 / bpm;
            let score = 0, hits = 0;
            for (const time of times) {
                const nearest = Math.round((time - times[0]) / interval) * interval + times[0];
                const error = Math.abs(time - nearest);
                if (error < interval * 0.12) { score += 1 - error / (interval * 0.12); hits++; }
            }
            scores.push({ bpm, score: score + hits * 0.12 });
        }
        scores.sort((a, b) => b.score - a.score);
        const best = scores[0];
        const second = scores[1] || { score: 0 };
        const confidence = Math.max(0, Math.min(1, (best.score - second.score) / Math.max(1, best.score)));
        return { bpm: Math.round(best.bpm * 10) / 10, phaseMs: times[0], confidence };
    }

    _buildBeatGrid(peaks, bpm, phaseMs) {
        if (peaks.length < 2) return peaks.map(p => p.timeMs);
        const interval = 60000 / Math.max(40, bpm);
        const endMs = this.duration * 1000;
        const grid = [];
        for (let t = phaseMs; t < endMs; t += interval) grid.push(t);
        // Only expose grid beats supported by nearby onsets; retain transient timing.
        return grid.map(t => {
            let nearest = null, distance = Infinity;
            for (const peak of peaks) { const d = Math.abs(peak.timeMs - t); if (d < distance) { distance = d; nearest = peak.timeMs; } }
            return nearest !== null && distance <= interval * 0.22 ? nearest : t;
        }).filter((t, i, a) => i === 0 || t - a[i - 1] > 80);
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
