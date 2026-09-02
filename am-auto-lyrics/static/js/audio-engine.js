/**
 * AM Auto Lyrics - High-Performance Web Audio & Beat Detection Engine
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
     * Loads and decodes an audio file (File or Blob or ArrayBuffer)
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

        // Perform automated beat & energy detection
        this.detectBeats();
        return {
            duration: this.duration,
            durationMs: Math.round(this.duration * 1000),
            bpm: this.detectedBpm,
            beatsCount: this.detectedBeats.length
        };
    }

    /**
     * Automated Sub-Band Energy Beat Detection Algorithm
     */
    detectBeats() {
        if (!this.audioBuffer) return;

        const rawData = this.audioBuffer.getChannelData(0);
        const sampleRate = this.audioBuffer.sampleRate;
        
        // Window size of 1024 samples (~23ms at 44.1kHz)
        const frameSize = 1024;
        const totalFrames = Math.floor(rawData.length / frameSize);
        const energies = new Float32Array(totalFrames);

        for (let i = 0; i < totalFrames; i++) {
            let sum = 0;
            const start = i * frameSize;
            for (let j = 0; j < frameSize; j++) {
                const val = rawData[start + j];
                sum += val * val;
            }
            energies[i] = sum / frameSize;
        }

        // Dynamic thresholding: compare instant energy to local average (window of ~43 frames = ~1s)
        const localWindow = 43;
        const detectedBeatsMs = [];
        const minBeatDistanceMs = 280; // Max ~215 BPM to prevent jitter
        let lastBeatTimeMs = -minBeatDistanceMs;

        for (let i = localWindow; i < totalFrames - localWindow; i++) {
            let localAvg = 0;
            for (let w = -localWindow; w <= localWindow; w++) {
                localAvg += energies[i + w];
            }
            localAvg /= (2 * localWindow + 1);

            const varianceMultiplier = 1.35; // Threshold sensitivity
            const timeMs = (i * frameSize / sampleRate) * 1000;

            if (energies[i] > localAvg * varianceMultiplier && (timeMs - lastBeatTimeMs) >= minBeatDistanceMs) {
                detectedBeatsMs.push(Math.round(timeMs));
                lastBeatTimeMs = timeMs;
            }
        }

        this.detectedBeats = detectedBeatsMs;

        // Estimate BPM from peak intervals
        if (detectedBeatsMs.length >= 2) {
            const intervals = [];
            for (let i = 1; i < detectedBeatsMs.length; i++) {
                const diff = detectedBeatsMs[i] - detectedBeatsMs[i - 1];
                if (diff >= 270 && diff <= 1500) {
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
     * Manual Tap to Beat recorder
     */
    tapBeat() {
        const currentMs = Math.round(this.getCurrentTime() * 1000);
        this.tappedBeats.push(currentMs);
        this.tappedBeats.sort((a, b) => a - b);
        return currentMs;
    }
}
