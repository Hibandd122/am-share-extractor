# 🎵 AM Auto Lyrics · Alight Motion Beat Sync & Lyric XML Generator

> **Automated beat detection, lyrics alignment, and authentic kinetic typography XML generator for Alight Motion.**

Transform any audio track and song lyrics into ready-to-import **Alight Motion Scene XML packages** with smooth typewriter reveals, pulse bounces, and beat bookmarks.

---

## 🌟 Features

- **🎧 Audio Beat & Onset Detection**: Web Audio FFT energy analyzer calculates BPM and automatically places beat bookmarks (`<bookmark t="..."/>`).
- **📝 Smart Lyric Alignment**: Supports raw text lyrics, synchronized LRC files (`[mm:ss.xx]`), and SRT subtitles.
- **⚡ Tap-to-Beat (Spacebar)**: Record custom beat timing dynamically while listening to the audio.
- **🎨 Authentic Kinetic Presets**:
  - `typewriter`: Character-by-character smooth kinetic reveal with CubicBezier easing (`0.0 0.0 0.56 1.0`) and fade in/out.
  - `kinetic_pop`: Energetic scale pulse that pops on the bass drop.
  - `neon_glow`: Cyberpunk glow with smooth upward slide.
  - `minimal_clean`: Elegant fade and kerning tracking expand.
- **🔤 Google Fonts Integration**: Patrick Hand, Montserrat, Outfit, Be Vietnam Pro, Quicksand, Inter, Caveat.
- **📱 Multi-Platform Output**: Generates 100% valid XML compatible with Alight Motion 6.x on iOS & Android.

---

## 🚀 Quick Start (Web Studio)

```bash
cd am-auto-lyrics
python app.py
```
Open **http://127.0.0.1:5001** in your browser.

---

## 💻 Command Line Usage (CLI)

```bash
# Generate lyric XML from lyrics text and BPM
python cli.py --lyrics "lyrics.txt" --bpm 128 --output "my_song_am.xml" --preset typewriter

# Specify custom resolution (e.g. 16:9 Landscape)
python cli.py --lyrics "lyrics.lrc" --bpm 135 --resolution 1920x1080 --title "Neon Track"
```
