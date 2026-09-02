"""
AM Auto Lyrics - Web Application Server
"""

import os
import sys
from flask import Flask, request, Response, render_template, jsonify

# Add core directory to Python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.xml_generator import generate_alight_motion_xml
from core.lyric_aligner import parse_raw_lyrics, align_lyrics_to_beats
from core.presets import PRESETS, AVAILABLE_FONTS

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static",
)


@app.route("/", methods=["GET"])
def index():
    """Renders the main Auto Lyrics Studio."""
    return render_template("index.html")


@app.route("/api/generate-xml", methods=["POST"])
def api_generate_xml():
    """
    Generates and returns an authentic Alight Motion XML project file.
    """
    data = request.get_json(silent=True) or {}
    title = data.get("title", "AM Lyrics Project").strip()
    width = int(data.get("width", 1080))
    height = int(data.get("height", 1920))
    fps = int(data.get("fps", 60))
    total_time_ms = int(data.get("total_time_ms", 30000))
    preset_id = data.get("preset_id", "typewriter")
    font_tag = data.get("font_tag", "googlefonts?name=Patrick Hand&weight=400")
    text_color_hex = data.get("text_color_hex", "#FFFFFFFF")
    bookmarks = data.get("bookmarks", [])
    lyrics = data.get("lyrics", [])

    if not lyrics:
        return jsonify({"error": "No lyrics lines provided."}), 400

    xml_output = generate_alight_motion_xml(
        lyrics=lyrics,
        bookmarks_ms=bookmarks,
        title=title,
        width=width,
        height=height,
        fps=fps,
        total_time_ms=total_time_ms,
        preset_id=preset_id,
        font_tag=font_tag,
        text_color_hex=text_color_hex,
    )

    clean_filename = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in title)
    return Response(
        xml_output,
        mimetype="application/xml; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{clean_filename}.xml"'
        },
    )


@app.route("/api/parse-lyrics", methods=["POST"])
def api_parse_lyrics():
    """Parses raw text / LRC / SRT into structured lyric items."""
    data = request.get_json(silent=True) or {}
    raw_text = data.get("text", "")
    items = parse_raw_lyrics(raw_text)
    return jsonify({"success": True, "lyrics": items, "count": len(items)})


@app.route("/api/presets", methods=["GET"])
def api_presets():
    """Returns available animation presets and fonts."""
    return jsonify({
        "presets": PRESETS,
        "fonts": AVAILABLE_FONTS,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"[*] Starting AM Auto Lyrics Studio on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
