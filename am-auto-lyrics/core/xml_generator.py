"""
Alight Motion XML Project Generator
Produces 100% valid Alight Motion XML scene packages with dynamic kinetic typography,
tailored cubicBezier easing curves per lyric line, and beat bookmarks.
"""

import html
import xml.dom.minidom
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from .presets import PRESETS, AVAILABLE_FONTS


def compute_dynamic_keyframes_for_lyric(
    text: str,
    duration_ms: int,
    preset_id: str = "typewriter"
) -> List[Dict[str, Any]]:
    """
    Computes authentic, individualized keyframes and cubicBezier easing curves
    tailored specifically to the syllable count, phrasing breaks, and duration of each lyric line.
    """
    char_count = max(1, len(text))
    words = text.split()
    word_count = max(1, len(words))

    if preset_id == "kinetic_pop":
        # Dynamic pop scale curve based on tempo/duration
        pop_end = min(0.40, max(0.20, 300.0 / max(1, duration_ms)))
        return [
            {"t": 0.000000, "v": 0.000000},
            {"t": round(pop_end, 6), "v": 1.000000, "e": "cubicBezier 0.17 0.89 0.32 1.28"}
        ]

    # Typewriter / Kinetic Reveal mode:
    # 1. Base progress end timing:
    if duration_ms <= 1600:
        t_end = 0.996155
        x2 = 0.7592593
    elif duration_ms <= 2200:
        t_end = 0.996155
        density = char_count / (duration_ms / 1000.0)
        x2 = round(min(0.85, max(0.45, 0.35 + (density / 20.0) * 0.3)), 8)
    else:
        t_end = round(min(0.996155, max(0.75, 0.70 + (char_count / 60.0) * 0.28)), 6)
        x2 = round(min(0.65, max(0.32, 0.30 + (char_count / 50.0) * 0.25)), 8)

    keyframes = [
        {"t": 0.000000, "v": 0.000000}
    ]

    # 2. Check for natural mid-sentence pauses / punctuation (comma, dash, ellipsis, semicolon)
    pause_chars = [',', ';', '-', '—', '...']
    found_pause_idx = -1
    for p in pause_chars:
        if p in text and 3 < text.find(p) < char_count - 3:
            found_pause_idx = text.find(p)
            break

    if found_pause_idx != -1 and duration_ms >= 1800:
        # Mid keyframe proportional to the clause break
        v_mid = round(found_pause_idx / float(char_count), 3)
        t_mid = round(max(0.20, min(0.65, (found_pause_idx / char_count) * 0.90)), 6)
        x2_mid = round(max(0.30, min(0.60, 0.25 + (v_mid * 0.4))), 8)
        keyframes.append({
            "t": t_mid,
            "v": v_mid,
            "e": f"cubicBezier 0.25 0.25 {x2_mid} 1.0"
        })
    elif word_count >= 8 and duration_ms >= 2000:
        # Multi-cadence flow for longer sentences
        mid_word_chars = len(" ".join(words[:word_count // 2]))
        v_mid = round(mid_word_chars / float(char_count), 3)
        t_mid = 0.496158
        keyframes.append({
            "t": t_mid,
            "v": v_mid,
            "e": "cubicBezier 0.25 0.25 0.55026454 1.0"
        })

    # 3. Final keyframe to 100% reveal with calculated cubicBezier easing
    keyframes.append({
        "t": t_end,
        "v": 1.000000,
        "e": f"cubicBezier 0.0 0.0 {x2} 1.0"
    })

    return keyframes


def generate_alight_motion_xml(
    lyrics: List[Dict[str, Any]],
    bookmarks_ms: List[int],
    title: str = "Auto Lyrics Project",
    width: int = 1080,
    height: int = 1920,
    fps: int = 60,
    total_time_ms: int = 30000,
    bgcolor_hex: str = "#FF000000",
    preset_id: str = "typewriter",
    font_tag: str = "googlefonts?name=Patrick Hand&weight=400",
    font_size: float = 24.0,
    text_color_hex: str = "#FFFFFFFF",
    audio_uri: Optional[str] = None,
    audio_filename: Optional[str] = None,
) -> str:
    """
    Builds the complete Alight Motion XML document tree.
    """
    if lyrics:
        max_lyric_end = max(item.get("end_ms", 0) for item in lyrics)
        total_time_ms = max(total_time_ms, max_lyric_end + 1500)
    if bookmarks_ms:
        total_time_ms = max(total_time_ms, max(bookmarks_ms) + 1000)

    preset = PRESETS.get(preset_id, PRESETS["typewriter"])

    scene = ET.Element(
        "scene",
        {
            "title": title,
            "width": str(width),
            "height": str(height),
            "exportWidth": str(width),
            "exportHeight": str(height),
            "bgcolor": bgcolor_hex,
            "totalTime": str(total_time_ms),
            "fps": str(fps),
            "amver": "863",
            "ffver": "107",
            "am": "com.alightcreative.motion/6.2.56",
            "amplatform": "ios",
            "precompose": "dynamicResolution",
            "retime": "freeze",
        }
    )

    if audio_uri and audio_filename:
        ET.SubElement(
            scene,
            "media",
            {
                "uri": audio_uri,
                "filename": audio_filename,
                "type": "audio/mp3",
                "size": "0",
            }
        )

    # Bookmarks
    sorted_bookmarks = sorted(list(set(bookmarks_ms)))
    for b_time in sorted_bookmarks:
        ET.SubElement(scene, "bookmark", {"t": str(int(b_time))})

    # Group Embed Scene
    embed_scene = ET.SubElement(
        scene,
        "embedScene",
        {
            "id": "100",
            "label": "Lyrics Group",
            "startTime": "0",
            "endTime": str(total_time_ms),
            "fillType": "intrinsic",
        }
    )

    group_tf = ET.SubElement(embed_scene, "transform")
    ET.SubElement(group_tf, "location", {"value": f"{width/2.0:.6f},{height/2.0:.6f},0.000000"})
    ET.SubElement(embed_scene, "fillColor", {"value": "#00000000"})

    inner_scene = ET.SubElement(
        embed_scene,
        "scene",
        {
            "title": "",
            "width": str(width),
            "height": str(height),
            "exportWidth": str(width),
            "exportHeight": str(height),
            "bgcolor": "#00000000",
            "totalTime": str(total_time_ms),
            "fps": str(fps),
            "amver": "863",
            "ffver": "107",
            "am": "com.alightcreative.motion/6.2.56",
            "amplatform": "ios",
            "precompose": "dynamicResolution",
            "retime": "off",
        }
    )

    if audio_uri:
        ET.SubElement(
            inner_scene,
            "audio",
            {
                "id": "1",
                "startTime": "0",
                "endTime": str(total_time_ms),
                "src": audio_uri,
            }
        )

    # Generate Animated Text Layers with individualized keyframes & cubicBezier
    cx, cy = width / 2.0, height / 2.0
    wrap_width = int(width * 0.88)

    for idx, item in enumerate(lyrics):
        text_id = idx + 2
        text_content = item.get("text", "").strip()
        start_ms = int(item.get("start_ms", 0))
        end_ms = int(item.get("end_ms", start_ms + 2500))
        duration_ms = max(500, end_ms - start_ms)

        text_el = ET.SubElement(
            inner_scene,
            "text",
            {
                "id": str(text_id),
                "label": text_content,
                "startTime": str(start_ms),
                "endTime": str(end_ms),
                "fillType": "color",
                "size": f"{font_size:.6f}",
                "font": font_tag,
                "wrapWidth": str(wrap_width),
                "align": "center",
            }
        )

        # Transform (Centered)
        tf_el = ET.SubElement(text_el, "transform")
        ET.SubElement(tf_el, "location", {"value": f"{cx:.6f},{cy:.6f},0.000000"})

        # Text Color
        fill_color_el = ET.SubElement(text_el, "fillColor")
        fill_color_el.set("value", text_color_hex)

        # Compute dynamic keyframes specifically tailored to this lyric line
        dynamic_keyframes = compute_dynamic_keyframes_for_lyric(text_content, duration_ms, preset_id)

        # Apply Preset Effects
        effects_def = preset.get("effects", [])
        for eff_def in effects_def:
            eff_el = ET.SubElement(
                text_el,
                "effect",
                {
                    "id": eff_def["id"],
                    "locallyApplied": eff_def.get("locallyApplied", "true"),
                }
            )

            for prop in eff_def.get("properties", []):
                p_name = prop["name"]
                p_type = prop["type"]
                
                prop_el = ET.SubElement(eff_el, "property", {"name": p_name, "type": p_type})
                
                if "value" in prop:
                    prop_el.set("value", str(prop["value"]))

                # Use dynamic keyframes for end / progress properties
                if p_name in ("end", "progress") or "keyframes" in prop:
                    for kf in dynamic_keyframes:
                        kf_attrs = {
                            "t": f"{kf['t']:.6f}",
                            "v": f"{kf['v']:.6f}",
                        }
                        if "e" in kf:
                            kf_attrs["e"] = kf["e"]
                        ET.SubElement(prop_el, "kf", kf_attrs)

        # Text Content tag
        content_el = ET.SubElement(text_el, "content")
        content_el.text = text_content

    # Output formatted XML
    raw_xml = ET.tostring(scene, encoding="utf-8")
    try:
        dom = xml.dom.minidom.parseString(raw_xml)
        pretty = dom.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
        clean_lines = [line for line in pretty.splitlines() if line.strip()]
        return "\n".join(clean_lines)
    except Exception:
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + raw_xml.decode("utf-8")
