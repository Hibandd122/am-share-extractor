# ⚡ Nexus Alight Motion Share Extractor (V2.0)

> **High-Performance XML scene extractor, layer inspector, and media package downloader for Alight Motion share links.**

Bypasses standard in-app import and Firebase Storage restrictions to extract scene descriptors, parse layer hierarchies, generate interactive SVG visualizations, and download individual media assets.

---

## 🌟 Key Features

- **⚡ Direct Firebase Storage Bypass:** Directly queries Firebase Cloud Storage REST endpoints using reconstructed object paths without requiring app authentication or import limits.
- **🎨 Interactive Studio Preview:** Visualizes project stage layouts with real-time SVG rendering, pan & zoom canvas controls, and layer highlighting sync.
- **🗂️ Deep Layer Hierarchy Inspector:** Explores vector shapes, embedded scenes, text properties, keyframes, and applied visual effects.
- **📦 Media Asset Browser & Extractor:** Extracts images, video clips, and audio tracks bundled inside the project package with 1-click downloads.
- **✨ XML Beautifier & Cleaner:** Exports clean, indented XML ready for inspection or direct import.
- **📑 Batch Link Inspector:** Analyzes multiple Alight Motion share links in parallel.
- **💻 RESTful JSON API:** Ready-to-integrate endpoints for bots, webapps, and automation scripts.
- **🛠️ Modular Architecture:** Clean separation of concerns (`core/`, `templates/`, `static/`, `api/`).

---

## 🏗️ Project Architecture

```
am-share-extractor/
├── api/
│   └── index.py             # Flask Web Server & Vercel Serverless Entrypoint
├── core/
│   ├── __init__.py          # Core package exports
│   ├── extractor.py         # URL parsing, Firebase Storage downloader, ZIP/asset extraction
│   ├── parser.py            # XML parser, metadata extraction, aspect ratio, beautifier
│   └── renderer.py          # Interactive SVG scene generator, HTML/JSON layer trees
├── templates/
│   ├── base.html            # Cyberpunk Glassmorphism base layout & theme
│   ├── index.html           # Landing page with Instant URL controls & quick stats
│   ├── preview.html         # Studio View (Canvas, Layer Tree, Media Gallery, XML Viewer)
│   └── batch.html           # Batch link processing pipeline
├── static/
│   ├── css/
│   │   ├── style.css        # Glassmorphism design system & animations
│   │   └── preview.css      # Studio workspace styles
│   └── js/
│       ├── app.js           # AJAX live inspector, history & toast notifications
│       └── preview.js       # Canvas zoom/pan, layer sync, code copy
├── am_share_to_xml.py       # Standalone CLI tool
├── requirements.txt         # Dependencies (Flask, Werkzeug)
└── vercel.json              # Serverless routing configuration
```

---

## 🚀 Quick Start (Web Server)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Locally
```bash
python api/index.py
```
Open **http://127.0.0.1:5000** in your browser.

---

## 🖥️ Command Line Interface (CLI)

```bash
# Basic extraction to XML
python am_share_to_xml.py "https://alightcreative.com/am/share/u/.../p/..."

# View detailed project specifications
python am_share_to_xml.py <link> --info

# Save formatted & beautified XML
python am_share_to_xml.py <link> --beautify -o project.xml

# Download full ZIP package (XML + all media assets)
python am_share_to_xml.py <link> --save-zip project.zip

# Extract only media assets (images, videos, audio) into a folder
python am_share_to_xml.py <link> --extract-media ./media_assets/

# Output project metadata as JSON
python am_share_to_xml.py <link> --json
```

---

## 🔌 REST API Endpoints

### 1. Project Information (`GET /api/info`)
```http
GET /api/info?url=https://alightcreative.com/am/share/u/.../p/...
```
**Response:**
```json
{
  "success": true,
  "user_id": "cSRKE4GLtKT7GayBmNth6HXsyjz2",
  "package_id": "RNP1b8PlJR-6a4e8d2307e72b4a",
  "metadata": {
    "title": "Neon Shake Effect",
    "resolution": "1080 × 1920",
    "aspect_ratio": "9:16 (Portrait / Reel)",
    "fps": 60,
    "duration_formatted": "00:08.50",
    "total_layers": 14,
    "fonts_used": ["Montserrat-Bold"],
    "effects_used": ["Glow", "Motion Blur", "Directional Blur"]
  },
  "package": {
    "media_count": 3,
    "media_files": [...]
  }
}
```

### 2. Download File (`GET /extract`)
```http
GET /extract?mode=full&url=...       # Download full project .zip
GET /extract?mode=xml&url=...        # Download raw scene .xml
GET /extract?mode=beautify&url=...   # Download formatted .xml
```

### 3. Stream Individual Asset (`GET /api/asset`)
```http
GET /api/asset?url=...&file=image_01.png
```

---

## ☁️ Deployment to Vercel

This repository is pre-configured for instant zero-config deployment on Vercel:
1. Push repository to GitHub.
2. Import repository on [Vercel](https://vercel.com).
3. The serverless function will automatically route all requests via `vercel.json` to `api/index.py`.

---

## 📜 License & Disclaimer
This project is for educational and reverse-engineering research purposes only.
All trademarks belong to their respective owners.
