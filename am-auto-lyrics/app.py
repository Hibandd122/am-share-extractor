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

        user_lines = [l.strip() for l in raw_lyrics_text.splitlines() if l.strip()]

        # Collect all recognized words with start and end timestamps
        all_words = []
        for seg in segments:
            for w in seg.get("words", []):
                all_words.append({
                    "word": w["word"].strip(),
                    "clean": "".join(c.lower() for c in w["word"] if c.isalnum()),
                    "start_ms": int(w["start"] * 1000),
                    "end_ms": int(w["end"] * 1000)
                })

        bookmarks = []
        final_lyrics = []

        if user_lines and all_words:
            import difflib

            word_ptr = 0
            total_words = len(all_words)

            for idx, u_line in enumerate(user_lines):
                u_words = ["".join(c.lower() for c in w if c.isalnum()) for w in u_line.split() if w.strip()]
                if not u_words:
                    continue

                best_score = -1
                best_range = (word_ptr, min(total_words, word_ptr + len(u_words)))

                # Search window around word_ptr
                search_end = min(total_words, word_ptr + len(u_words) * 3 + 6)
                for s in range(word_ptr, min(search_end, total_words)):
                    for e in range(s + 1, min(s + len(u_words) + 8, total_words + 1)):
                        sub = " ".join(all_words[i]["clean"] for i in range(s, e))
                        ref = " ".join(u_words)
                        ratio = difflib.SequenceMatcher(None, sub, ref).ratio()
                        if ratio > best_score:
                            best_score = ratio
                            best_range = (s, e)

                s_idx, e_idx = best_range
                if e_idx > s_idx and s_idx < total_words:
                    start_ms = all_words[s_idx]["start_ms"]
                    end_ms = all_words[min(e_idx - 1, total_words - 1)]["end_ms"]
                    word_ptr = e_idx
                else:
                    prev_end = final_lyrics[-1]["end_ms"] if final_lyrics else 1000
                    start_ms = prev_end + 300
                    end_ms = prev_end + 2500

                # Ensure minimum line duration of 1.2s for clean readability
                if end_ms - start_ms < 1200:
                    end_ms = start_ms + 1500

                final_lyrics.append({
                    "id": idx + 1,
                    "text": u_line,
                    "start_ms": start_ms,
                    "end_ms": end_ms
                })
                bookmarks.append(start_ms)
        elif segments:
            for idx, seg in enumerate(segments):
                s_ms = int(seg["start"] * 1000)
                e_ms = int(seg["end"] * 1000)
                final_lyrics.append({
                    "id": idx + 1,
                    "text": seg["text"].strip(),
                    "start_ms": s_ms,
                    "end_ms": e_ms
                })
                bookmarks.append(s_ms)

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
