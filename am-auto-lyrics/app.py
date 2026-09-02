"""
AM Auto Lyrics - Web Application Server
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
app.config["MAX_CONTENT_LENGTH"] = 128 * 1024 * 1024


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


import tempfile

_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            print("[*] Loading Whisper base model into memory...")
            _whisper_model = whisper.load_model("base")
            print("[OK] Whisper base model loaded successfully.")
        except Exception as e:
            print(f"[!] Failed to load whisper: {e}")
    return _whisper_model


@app.route("/api/whisper-align", methods=["POST"])
def api_whisper_align():
    """
    AI Speech-to-Text & Vocal Alignment using Whisper.
    Transcribes and detects precise vocal line boundaries with millisecond precision.
    """
    if "audio" not in request.files:
        return jsonify({"success": False, "error": "No audio file uploaded."}), 400

    audio_file = request.files["audio"]
    raw_lyrics_text = request.form.get("lyrics_text", "").strip()

    model = get_whisper_model()
    if not model:
        return jsonify({"success": False, "error": "Whisper is not available on server."}), 500

    # Save to temp file
    suffix = os.path.splitext(audio_file.filename)[1] or ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        # Transcribe with word timestamps
        res = model.transcribe(tmp_path, language="vi", word_timestamps=True)
        segments = res.get("segments", [])

        # Extract vocal lines from segments & words
        bookmarks = []
        user_lines = [l.strip() for l in raw_lyrics_text.splitlines() if l.strip()]

        phrase_list = []
        for seg in segments:
            words = seg.get("words", [])
            if not words:
                s_ms = int(seg["start"] * 1000)
                e_ms = int(seg["end"] * 1000)
                phrase_list.append({"text": seg["text"].strip(), "start_ms": s_ms, "end_ms": e_ms})
                bookmarks.append(s_ms)
                continue

            # Group words by pause >= 380ms or punctuation
            cur_words = []
            cur_start = int(words[0]["start"] * 1000)
            for i, w in enumerate(words):
                cur_words.append(w["word"])
                w_end = int(w["end"] * 1000)
                
                has_comma_or_period = any(p in w["word"] for p in (',', '.', ';', '?', '!'))
                next_pause = False
                if i < len(words) - 1:
                    next_start = int(words[i + 1]["start"] * 1000)
                    if next_start - w_end >= 380:
                        next_pause = True

                if (has_comma_or_period and len(cur_words) >= 4) or next_pause or i == len(words) - 1:
                    phrase_text = "".join(cur_words).strip()
                    if phrase_text:
                        phrase_list.append({
                            "text": phrase_text,
                            "start_ms": cur_start,
                            "end_ms": w_end
                        })
                        bookmarks.append(cur_start)
                    cur_words = []
                    if i < len(words) - 1:
                        cur_start = int(words[i + 1]["start"] * 1000)

        # If user provided clean lyrics text, map clean text to detected timestamps
        final_lyrics = []
        if user_lines and phrase_list:
            for idx, u_text in enumerate(user_lines):
                if idx < len(phrase_list):
                    ts = phrase_list[idx]
                    final_lyrics.append({
                        "id": idx + 1,
                        "text": u_text,
                        "start_ms": ts["start_ms"],
                        "end_ms": ts["end_ms"]
                    })
                else:
                    last_end = final_lyrics[-1]["end_ms"] if final_lyrics else 1000
                    final_lyrics.append({
                        "id": idx + 1,
                        "text": u_text,
                        "start_ms": last_end + 300,
                        "end_ms": last_end + 2500
                    })
        else:
            final_lyrics = [
                {"id": i + 1, "text": p["text"], "start_ms": p["start_ms"], "end_ms": p["end_ms"]}
                for i, p in enumerate(phrase_list)
            ]

        return jsonify({
            "success": True,
            "lyrics": final_lyrics,
            "bookmarks": sorted(list(set(bookmarks))),
            "count": len(final_lyrics)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Lỗi xử lý Whisper: {str(e)}"}), 500
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"[*] Starting AM Auto Lyrics Studio on http://127.0.0.1:{port}")
    # Preload Whisper so first request is instant
    get_whisper_model()
    # Run with use_reloader=False so Python library files don't trigger unexpected server restarts
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
