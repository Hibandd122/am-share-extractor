/**
 * AM Auto Lyrics - Studio Workspace & Live Canvas Animator
 */

const audioEngine = new AMAudioEngine();
let currentLyrics = [];
let activeLyricIndex = -1;

const SAMPLE_VIET_LYRICS = `Trước khi em đến, anh vốn là người thường
Chưa từng được yêu, chưa từng được thích
Ngày em bước tới, mang ánh nắng chiếu lên đây
Con tim của anh không còn được xích
Trái tim tan nát từ hôm nào
Nay được sống lại trong khoảnh khắc bình yên
Anh đâu tin nổi được thực tại
Luôn thầm tự hỏi, nghĩ chắc mình điên
Tháng 6, có cơn mưa bay bay lất phất
Bên những cuộc trò chuyện ngày mùa hạ nắng lên
Anh thầm tự hỏi làm sao ta có thể mãi được hò hẹn`;

document.addEventListener("DOMContentLoaded", () => {
    initAudioDropzone();
    initLyricsEditor();
    initPlaybackControls();
    initWaveformInteractions();
    initBeatSliders();
    initExportActions();
});

// Audio File Loading & Dropzone
function initAudioDropzone() {
    const dropzone = document.getElementById("audioDropzone");
    const fileInput = document.getElementById("audioFileInput");
    const statusBadge = document.getElementById("audioStatusBadge");
    const audioMeta = document.getElementById("audioMetaDisplay");

    dropzone.addEventListener("click", () => fileInput.click());

    ["dragenter", "dragover"].forEach(evt => {
        dropzone.addEventListener(evt, (e) => {
            e.preventDefault();
            dropzone.classList.add("dragover");
        });
    });

    ["dragleave", "drop"].forEach(evt => {
        dropzone.addEventListener(evt, (e) => {
            e.preventDefault();
            dropzone.classList.remove("dragover");
        });
    });

    dropzone.addEventListener("drop", (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) handleAudioFile(files[0]);
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) handleAudioFile(e.target.files[0]);
    });

    async function handleAudioFile(file) {
        statusBadge.textContent = "⌛ Decoding & Detecting Beats...";
        statusBadge.style.display = "inline-flex";

        try {
            const stats = await audioEngine.loadAudio(file);
            statusBadge.textContent = `✓ ${stats.bpm} BPM · ${stats.beatsCount} Beats Detected (${(stats.duration).toFixed(1)}s)`;
            
            // Auto align lyrics if present
            autoAlignLyrics();
            drawWaveform();
        } catch (err) {
            statusBadge.textContent = "✕ Failed to decode audio file.";
            statusBadge.style.color = "#f43f5e";
        }
    }
}

// Lyrics Editor
function initLyricsEditor() {
    const textarea = document.getElementById("lyricsInput");
    const sampleBtn = document.getElementById("loadSampleBtn");
    const alignBtn = document.getElementById("autoAlignBtn");

    if (sampleBtn) {
        sampleBtn.addEventListener("click", () => {
            textarea.value = SAMPLE_VIET_LYRICS;
            parseAndRenderLyrics();
        });
    }

    textarea.addEventListener("input", () => {
        parseAndRenderLyrics();
    });

    if (alignBtn) {
        alignBtn.addEventListener("click", () => {
            autoAlignLyrics();
        });
    }
}

function parseAndRenderLyrics() {
    const raw = document.getElementById("lyricsInput").value.trim();
    if (!raw) {
        currentLyrics = [];
        renderLyricList();
        return;
    }

    const lines = raw.split("\n").map(l => l.trim()).filter(l => l.length > 0);
    currentLyrics = lines.map((text, idx) => ({
        id: idx + 1,
        text: text,
        start_ms: 0,
        end_ms: 0
    }));

    if (audioEngine.audioBuffer) {
        autoAlignLyrics();
    } else {
        renderLyricList();
    }
}

function autoAlignLyrics() {
    if (currentLyrics.length === 0) return;

    const beats = audioEngine.tappedBeats.length > 0 ? audioEngine.tappedBeats : audioEngine.detectedBeats;
    const totalMs = Math.round((audioEngine.duration || 30) * 1000);
    const numLines = currentLyrics.length;

    if (beats.length >= numLines) {
        const step = Math.floor(beats.length / numLines);
        for (let i = 0; i < numLines; i++) {
            const s = beats[i * step];
            const nextStart = (i < numLines - 1) ? beats[(i + 1) * step] : (s + 3500);
            currentLyrics[i].start_ms = Math.max(0, s);
            currentLyrics[i].end_ms = Math.max(s + 2000, Math.min(nextStart, s + 4000));
        }
    } else {
        const leadIn = 1000;
        const perLine = Math.max(2500, (totalMs - leadIn - 1500) / numLines);
        for (let i = 0; i < numLines; i++) {
            const s = Math.round(leadIn + i * perLine);
            currentLyrics[i].start_ms = s;
            currentLyrics[i].end_ms = Math.round(s + perLine * 0.92);
        }
    }

    renderLyricList();
}

function evalCubicBezier(x1, y1, x2, y2, t) {
    const cx = 3 * x1;
    const bx = 3 * (x2 - x1) - cx;
    const ax = 1 - cx - bx;

    const cy = 3 * y1;
    const by = 3 * (y2 - y1) - cy;
    const ay = 1 - cy - by;

    function sampleX(t) { return ((ax * t + bx) * t + cx) * t; }
    function sampleY(t) { return ((ay * t + by) * t + cy) * t; }

    let t0 = 0, t1 = 1, t2 = t;
    for (let i = 0; i < 8; i++) {
        const x2_val = sampleX(t2);
        if (Math.abs(x2_val - t) < 0.001) break;
        if (t > x2_val) t0 = t2;
        else t1 = t2;
        t2 = (t1 + t0) / 2;
    }
    return Math.max(0, Math.min(1, sampleY(t2)));
}

function updateActiveLyric(curMs) {
    let foundIdx = -1;
    for (let i = 0; i < currentLyrics.length; i++) {
        if (curMs >= currentLyrics[i].start_ms && curMs <= currentLyrics[i].end_ms) {
            foundIdx = i;
            break;
        }
    }

    const liveTextEl = document.getElementById("canvasLiveText");
    const fontSelect = document.getElementById("fontSelect");
    const presetSelect = document.getElementById("presetSelect");

    // Apply selected font family to live stage
    if (fontSelect && liveTextEl) {
        const fontName = fontSelect.options[fontSelect.selectedIndex]?.text?.split('(')[0]?.trim() || "Patrick Hand";
        liveTextEl.style.fontFamily = `"${fontName}", var(--font-main)`;
    }

    if (foundIdx !== -1) {
        const item = currentLyrics[foundIdx];
        const duration = Math.max(1, item.end_ms - item.start_ms);
        const rawProgress = Math.max(0, Math.min(1, (curMs - item.start_ms) / duration));

        const preset = presetSelect ? presetSelect.value : "typewriter";

        if (preset === "typewriter") {
            // Eased typewriter progressive character reveal
            const easedProgress = evalCubicBezier(0.0, 0.0, 0.56, 1.0, rawProgress);
            const totalChars = item.text.length;
            const revealCount = Math.min(totalChars, Math.max(0, Math.floor(easedProgress * totalChars)));

            const revealed = item.text.slice(0, revealCount);
            const pending = item.text.slice(revealCount);

            liveTextEl.innerHTML = `
                <span class="revealed-text">${escapeHtml(revealed)}</span>
                <span class="typewriter-cursor"></span>
                <span class="pending-text">${escapeHtml(pending)}</span>
            `;
            liveTextEl.style.transform = "scale(1.02)";
            liveTextEl.style.opacity = "1";
        } else if (preset === "kinetic_pop") {
            // Scale bounce on onset
            const scale = rawProgress < 0.3 ? 1.0 + (1.0 - rawProgress / 0.3) * 0.25 : 1.0;
            liveTextEl.innerHTML = `<span class="revealed-text">${escapeHtml(item.text)}</span>`;
            liveTextEl.style.transform = `scale(${scale.toFixed(3)})`;
            liveTextEl.style.opacity = "1";
        } else if (preset === "neon_glow") {
            // Cyber glow pulsating
            const glow = 15 + Math.sin(rawProgress * Math.PI * 4) * 10;
            liveTextEl.innerHTML = `<span class="revealed-text" style="text-shadow: 0 0 ${glow}px #38bdf8, 0 0 ${glow*2}px #818cf8;">${escapeHtml(item.text)}</span>`;
            liveTextEl.style.transform = "translateY(-4px)";
            liveTextEl.style.opacity = "1";
        } else {
            // Minimal fade
            const opacity = Math.min(1, rawProgress * 3);
            liveTextEl.innerHTML = `<span class="revealed-text">${escapeHtml(item.text)}</span>`;
            liveTextEl.style.opacity = `${opacity}`;
            liveTextEl.style.transform = "scale(1)";
        }

        if (foundIdx !== activeLyricIndex) {
            activeLyricIndex = foundIdx;
            document.querySelectorAll(".lyric-item-row").forEach((row, i) => {
                if (i === activeLyricIndex) {
                    row.classList.add("active");
                    row.scrollIntoView({ behavior: "smooth", block: "nearest" });
                } else {
                    row.classList.remove("active");
                }
            });
        }
    } else {
        if (activeLyricIndex !== -1) {
            activeLyricIndex = -1;
            document.querySelectorAll(".lyric-item-row").forEach(row => row.classList.remove("active"));
        }
        if (liveTextEl) {
            liveTextEl.innerHTML = `<span style="opacity: 0.35;">[ Lyrics Live Preview Stage ]</span>`;
            liveTextEl.style.transform = "scale(1)";
        }
    }
}

function renderLyricList() {
    const container = document.getElementById("lyricItemsContainer");
    if (!container) return;

    container.innerHTML = "";
    if (currentLyrics.length === 0) {
        container.innerHTML = '<div style="color:var(--text-muted); text-align:center; padding:20px;">No lyrics loaded yet.</div>';
        return;
    }

    currentLyrics.forEach((item, idx) => {
        const row = document.createElement("div");
        row.className = "lyric-item-row" + (idx === activeLyricIndex ? " active" : "");
        row.id = `lyric-row-${idx}`;

        const startSec = (item.start_ms / 1000).toFixed(2);
        const endSec = (item.end_ms / 1000).toFixed(2);

        row.innerHTML = `
            <div style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                <strong>${idx + 1}.</strong> ${escapeHtml(item.text)}
            </div>
            <div class="lyric-timing">
                <span>${startSec}s - ${endSec}s</span>
            </div>
        `;

        row.addEventListener("click", () => {
            if (audioEngine.audioBuffer) {
                audioEngine.seek(item.start_ms / 1000);
            }
        });

        container.appendChild(row);
    });
}

// Playback and Tap to Beat Controls
function initPlaybackControls() {
    const playBtn = document.getElementById("playPauseBtn");
    const stopBtn = document.getElementById("stopBtn");
    const tapBtn = document.getElementById("tapBeatBtn");
    const timeDisplay = document.getElementById("playbackTimeDisplay");

    if (playBtn) {
        playBtn.addEventListener("click", () => {
            if (audioEngine.isPlaying) {
                audioEngine.pause();
                playBtn.innerHTML = "▶ Play";
            } else {
                audioEngine.play();
                playBtn.innerHTML = "⏸ Pause";
            }
        });
    }

    if (stopBtn) {
        stopBtn.addEventListener("click", () => {
            audioEngine.pause();
            audioEngine.seek(0);
            if (playBtn) playBtn.innerHTML = "▶ Play";
        });
    }

    // Spacebar Listener for Tap-to-Beat
    window.addEventListener("keydown", (e) => {
        if (e.code === "Space" && e.target.tagName !== "TEXTAREA" && e.target.tagName !== "INPUT") {
            e.preventDefault();
            triggerTapBeat();
        }
    });

    if (tapBtn) {
        tapBtn.addEventListener("click", () => triggerTapBeat());
    }

    function triggerTapBeat() {
        if (!audioEngine.isPlaying) {
            audioEngine.play();
            if (playBtn) playBtn.innerHTML = "⏸ Pause";
        }
        const ms = audioEngine.tapBeat();
        drawWaveform();
    }

    audioEngine.onPlaybackUpdate = (curSeconds) => {
        const curMs = Math.round(curSeconds * 1000);
        if (timeDisplay) {
            const mins = Math.floor(curSeconds / 60);
            const secs = (curSeconds % 60).toFixed(1);
            timeDisplay.textContent = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
        }

        // Update playhead on waveform
        const playhead = document.getElementById("timelinePlayhead");
        if (playhead && audioEngine.duration > 0) {
            const pct = (curSeconds / audioEngine.duration) * 100;
            playhead.style.left = `${pct}%`;
        }

        // Highlight active lyric
        updateActiveLyric(curMs);
    };

    audioEngine.onPlaybackEnded = () => {
        if (playBtn) playBtn.innerHTML = "▶ Play";
    };
// Waveform Canvas Rendering
function initWaveformInteractions() {
    const wrapper = document.getElementById("waveformWrapper");
    if (!wrapper) return;

    wrapper.addEventListener("click", (e) => {
        if (!audioEngine.audioBuffer) return;
        const rect = wrapper.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const ratio = clickX / rect.width;
        audioEngine.seek(ratio * audioEngine.duration);
    });
}

function drawWaveform() {
    const canvas = document.getElementById("waveformCanvas");
    if (!canvas || !audioEngine.audioBuffer) return;

    const ctx = canvas.getContext("2d");
    const width = canvas.width = canvas.parentElement.clientWidth;
    const height = canvas.height = canvas.parentElement.clientHeight;

    ctx.clearRect(0, 0, width, height);

    const rawData = audioEngine.audioBuffer.getChannelData(0);
    const step = Math.ceil(rawData.length / width);
    const amp = height / 2;

    // Draw waveform bars
    ctx.fillStyle = "rgba(56, 189, 248, 0.4)";
    for (let i = 0; i < width; i++) {
        let min = 1.0;
        let max = -1.0;
        for (let j = 0; j < step; j++) {
            const datum = rawData[(i * step) + j];
            if (datum < min) min = datum;
            if (datum > max) max = datum;
        }
        ctx.fillRect(i, (1 + min) * amp, 1, Math.max(1, (max - min) * amp));
    }

    // Draw beat lines
    const allBeats = audioEngine.tappedBeats.length > 0 ? audioEngine.tappedBeats : audioEngine.detectedBeats;
    const durationMs = audioEngine.duration * 1000;

    allBeats.forEach(bMs => {
        const x = (bMs / durationMs) * width;
        ctx.strokeStyle = "rgba(244, 63, 94, 0.7)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
    });
}

// Export XML Action
function initExportActions() {
    const exportBtn = document.getElementById("exportXmlBtn");
    if (!exportBtn) return;

    exportBtn.addEventListener("click", async () => {
        if (currentLyrics.length === 0) {
            alert("Please input at least one line of lyrics.");
            return;
        }

        const title = document.getElementById("projectTitleInput")?.value || "AM Auto Lyrics";
        const presetId = document.getElementById("presetSelect")?.value || "typewriter";
        const fontTag = document.getElementById("fontSelect")?.value || "googlefonts?name=Patrick Hand&weight=400";
        const resolution = document.getElementById("aspectRatioSelect")?.value || "1080x1920";
        
        const [w, h] = resolution.split("x").map(Number);
        const bookmarks = audioEngine.tappedBeats.length > 0 ? audioEngine.tappedBeats : audioEngine.detectedBeats;

        exportBtn.disabled = true;
        exportBtn.textContent = "⚡ Generating XML...";

        try {
            const res = await fetch("/api/generate-xml", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: title,
                    width: w,
                    height: h,
                    fps: 60,
                    total_time_ms: Math.round((audioEngine.duration || 30) * 1000),
                    preset_id: presetId,
                    font_tag: fontTag,
                    bookmarks: bookmarks,
                    lyrics: currentLyrics,
                })
            });

            if (!res.ok) throw new Error("Failed to generate XML on server");

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${title.replace(/[^a-zA-Z0-9_-]/g, "_")}.xml`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            alert("Error exporting XML: " + err.message);
        } finally {
            exportBtn.disabled = false;
            exportBtn.textContent = "⬇️ Export Alight Motion XML";
        }
    });
}

function initBeatSliders() {
    const offsetSlider = document.getElementById("beatOffsetSlider");
    const offsetDisplay = document.getElementById("offsetValueDisplay");
    const sensSlider = document.getElementById("beatSensSlider");
    const sensDisplay = document.getElementById("sensValueDisplay");

    if (offsetSlider && offsetDisplay) {
        offsetSlider.addEventListener("input", () => {
            const val = parseInt(offsetSlider.value, 10);
            offsetDisplay.textContent = `${val}ms`;
            if (audioEngine.audioBuffer) {
                audioEngine.detectBeats(parseFloat(sensSlider.value), val);
                autoAlignLyrics();
                drawWaveform();
            }
        });
    }

    if (sensSlider && sensDisplay) {
        sensSlider.addEventListener("input", () => {
            const val = parseFloat(sensSlider.value);
            sensDisplay.textContent = `${val.toFixed(2)}x`;
            if (audioEngine.audioBuffer) {
                audioEngine.detectBeats(val, parseInt(offsetSlider.value, 10));
                autoAlignLyrics();
                drawWaveform();
            }
        });
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
