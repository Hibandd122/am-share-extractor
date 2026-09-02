import math
import re
import xml.dom.minidom
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set, Tuple

KNOWN_EFFECTS = {
    "gaussianblur": "Gaussian Blur",
    "motionblur": "Motion Blur",
    "boxblur": "Box Blur",
    "directionalblur": "Directional Blur",
    "fastblur": "Fast Blur",
    "radialblur": "Radial Blur",
    "colortemperature": "Color Temperature",
    "colorgradient": "Color Gradient",
    "rgbshift": "RGB Shift",
    "chromatickey": "Chroma Key",
    "lumakey": "Luma Key",
    "tiles": "Tiles",
    "glow": "Glow",
    "dropshadow": "Drop Shadow",
    "innerglow": "Inner Glow",
}


def format_effect_name(raw_id: str) -> str:
    """Format effect ID into clean human-readable name."""
    if not raw_id:
        return ""
    suffix = raw_id.split(".")[-1].lower()
    if suffix in KNOWN_EFFECTS:
        return KNOWN_EFFECTS[suffix]
    
    last_part = raw_id.split(".")[-1]
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", last_part)
    return spaced.replace("_", " ").title()


def am_color_to_hex(val: Optional[str], fallback: str = "#000000") -> str:
    """
    Converts Alight Motion's color representation (#AARRGGBB or #RRGGBB)
    to standard CSS #RRGGBB format or fallback.
    """
    if not val:
        return fallback
    v = val.strip()
    # Check #AARRGGBB (8 hex digits) -> #RRGGBB (omit alpha or use hex)
    if re.fullmatch(r"#[0-9a-fA-F]{8}", v):
        alpha_hex = v[1:3]
        rgb_hex = v[3:]
        # If fully opaque or near opaque, just return #RRGGBB
        if alpha_hex.lower() == "ff":
            return f"#{rgb_hex}"
        try:
            alpha_float = int(alpha_hex, 16) / 255.0
            r = int(rgb_hex[0:2], 16)
            g = int(rgb_hex[2:4], 16)
            b = int(rgb_hex[4:6], 16)
            return f"rgba({r}, {g}, {b}, {alpha_float:.2f})"
        except Exception:
            return f"#{rgb_hex}"
    elif re.fullmatch(r"#[0-9a-fA-F]{6}", v):
        return v
    return v or fallback


def beautify_xml(xml_content: bytes | str) -> str:
    """
    Parses and formats XML with clean indentation and UTF-8 header.
    """
    if isinstance(xml_content, bytes):
        raw_text = xml_content.decode("utf-8", errors="replace")
    else:
        raw_text = xml_content

    try:
        dom = xml.dom.minidom.parseString(raw_text.encode("utf-8"))
        pretty_xml = dom.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
        lines = [line for line in pretty_xml.splitlines() if line.strip()]
        return "\n".join(lines)
    except Exception:
        return raw_text


def parse_xml_string(xml_bytes: bytes) -> ET.Element:
    """
    Parses XML bytes and returns the root or <scene> Element.
    """
    root = ET.fromstring(xml_bytes)
    scene = root if root.tag == "scene" else root.find(".//scene")
    if scene is None:
        raise ValueError("Could not find a valid <scene> node in the XML payload.")
    return scene


def calculate_aspect_ratio(width: float, height: float) -> str:
    """
    Calculates standard aspect ratio strings like 16:9, 9:16, 1:1, 4:5, 4:3, etc.
    """
    if width <= 0 or height <= 0:
        return "Unknown"
    
    ratio = width / height
    if abs(ratio - 16 / 9) < 0.05:
        return "16:9 (Landscape)"
    elif abs(ratio - 9 / 16) < 0.05:
        return "9:16 (Portrait / Reel)"
    elif abs(ratio - 1.0) < 0.05:
        return "1:1 (Square)"
    elif abs(ratio - 4 / 5) < 0.05:
        return "4:5 (Instagram Post)"
    elif abs(ratio - 4 / 3) < 0.05:
        return "4:3 (Standard)"
    elif abs(ratio - 21 / 9) < 0.05:
        return "21:9 (Ultrawide)"
    
    w_int, h_int = int(round(width)), int(round(height))
    gcd = math.gcd(w_int, h_int)
    if gcd > 10:
        return f"{w_int // gcd}:{h_int // gcd}"
    return f"{ratio:.2f}:1"


def parse_manifest(manifest_text: str) -> List[Dict[str, str]]:
    """
    Parses manifest.txt content (usually SHA1 hashes and file paths).
    """
    items = []
    if not manifest_text:
        return items

    lines = manifest_text.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            sha1 = parts[0]
            filename = " ".join(parts[1:])
            items.append({"sha1": sha1, "filename": filename})
        else:
            items.append({"sha1": "", "filename": line})
    return items


def parse_scene_metadata(scene: ET.Element, package_id: str = "") -> Dict[str, Any]:
    """
    Inspects and aggregates rich metadata from an Alight Motion <scene> element.
    """
    title = scene.get("title") or package_id or "Untitled Project"
    
    try:
        width = float(scene.get("width", 1920))
    except (ValueError, TypeError):
        width = 1920.0

    try:
        height = float(scene.get("height", 1080))
    except (ValueError, TypeError):
        height = 1080.0

    try:
        fps = float(scene.get("fps", 30))
    except (ValueError, TypeError):
        fps = 30.0

    try:
        time_scale = float(scene.get("timeScale", 1.0))
    except (ValueError, TypeError):
        time_scale = 1.0

    bgcolor_raw = scene.get("bgcolor", "#000000")
    bgcolor_css = am_color_to_hex(bgcolor_raw, "#000000")

    fonts_used: Set[str] = set()
    effects_used: Set[str] = set()
    media_references: List[Dict[str, str]] = []
    
    shapes_count = 0
    embed_scenes_count = 0
    text_count = 0
    media_layers_count = 0
    audio_layers_count = 0
    effects_count = 0

    max_end_time = 0.0

    def inspect_element(el: ET.Element, depth: int = 0):
        nonlocal shapes_count, embed_scenes_count, text_count, media_layers_count, audio_layers_count, effects_count, max_end_time
        
        start_time_val = el.get("startTime") or el.get("start")
        end_time_val = el.get("endTime") or el.get("end")
        if end_time_val:
            try:
                max_end_time = max(max_end_time, float(end_time_val))
            except ValueError:
                pass

        tag = el.tag
        if tag == "shape":
            shapes_count += 1
            shape_kind = el.get("s", "")
            fill_type = el.get("fillType", "")
            if fill_type == "media" or el.get("fillImage") or el.get("fillVideo"):
                media_layers_count += 1
        elif tag == "text":
            text_count += 1
            font_attr = el.get("font") or el.get("fontFamily")
            if font_attr:
                fonts_used.add(font_attr)
        elif tag == "embedScene":
            embed_scenes_count += 1
            sub_scene = el.find("./scene")
            if sub_scene is not None:
                for child in list(sub_scene):
                    inspect_element(child, depth + 1)
        elif tag == "audio":
            audio_layers_count += 1

        # Check font properties
        for prop in el.findall(".//property"):
            p_name = prop.get("name", "")
            p_val = prop.get("value", "")
            if "font" in p_name.lower() and p_val:
                fonts_used.add(p_val)

        # Check effects
        for eff in el.findall(".//effect"):
            effects_count += 1
            eff_id = eff.get("id", "")
            if eff_id:
                readable_name = format_effect_name(eff_id)
                if readable_name:
                    effects_used.add(readable_name)

    for el in list(scene):
        inspect_element(el)

    for m in scene.findall("./media"):
        media_references.append({
            "id": m.get("id", ""),
            "filename": m.get("filename", ""),
            "type": m.get("type", "unknown"),
            "width": m.get("width", "?"),
            "height": m.get("height", "?"),
            "duration": m.get("duration", "?"),
        })

    duration_sec = 0.0
    if max_end_time > 0:
        if max_end_time > 1000:
            duration_sec = max_end_time / 1000.0
        else:
            duration_sec = max_end_time
    
    mins = int(duration_sec // 60)
    secs = duration_sec % 60
    duration_formatted = f"{mins:02d}:{secs:05.2f}" if duration_sec > 0 else "N/A"

    total_layers = shapes_count + embed_scenes_count + text_count + audio_layers_count

    return {
        "title": title,
        "width": int(width),
        "height": int(height),
        "resolution": f"{int(width)} × {int(height)}",
        "aspect_ratio": calculate_aspect_ratio(width, height),
        "fps": int(fps) if fps.is_integer() else fps,
        "bgcolor_raw": bgcolor_raw,
        "bgcolor_css": bgcolor_css,
        "duration_sec": round(duration_sec, 2),
        "duration_formatted": duration_formatted,
        "total_layers": total_layers,
        "shapes_count": shapes_count,
        "embed_scenes_count": embed_scenes_count,
        "text_count": text_count,
        "media_layers_count": media_layers_count,
        "audio_layers_count": audio_layers_count,
        "effects_count": effects_count,
        "fonts_used": sorted(list(fonts_used)),
        "effects_used": sorted(list(effects_used)),
        "media_references": media_references,
    }
