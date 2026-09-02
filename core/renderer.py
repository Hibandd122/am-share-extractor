import html
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from .parser import am_color_to_hex


def render_svg(scene: ET.Element) -> str:
    """
    Renders an Alight Motion XML scene element into an interactive, visually rich SVG.
    Includes layer IDs, transform matrix/rotations, media placeholders, text labels,
    and SVG hover tooltips.
    """
    try:
        w = float(scene.get("width", 1920))
    except (ValueError, TypeError):
        w = 1920.0

    try:
        h = float(scene.get("height", 1080))
    except (ValueError, TypeError):
        h = 1080.0

    bg = am_color_to_hex(scene.get("bgcolor"), "#0a0a0f")

    parts = [
        f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" class="am-stage-svg" id="amStageSvg">',
        '<defs>',
        '  <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">',
        '    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>',
        '  </pattern>',
        '  <filter id="layerGlow" x="-20%" y="-20%" width="140%" height="140%">',
        '    <feGaussianBlur stdDeviation="6" result="blur" />',
        '    <feComposite in="SourceGraphic" in2="blur" operator="over" />',
        '  </filter>',
        '</defs>',
        f'<rect x="0" y="0" width="{w}" height="{h}" fill="{bg}" class="am-stage-bg"/>',
        f'<rect x="0" y="0" width="{w}" height="{h}" fill="url(#gridPattern)" class="am-stage-grid"/>',
    ]

    layer_index = 0

    def process_element(el: ET.Element, depth: int = 0):
        nonlocal layer_index
        if el.tag not in ("shape", "embedScene", "text"):
            return

        layer_index += 1
        layer_id = f"layer-{layer_index}"
        label = el.get("label") or el.tag
        label_esc = html.escape(label)
        shape_kind = el.get("s", "")
        fill_type = el.get("fillType", "")

        # Transform extraction
        loc = el.find("./transform/location")
        scl = el.find("./transform/scale")
        rot = el.find("./transform/rotation")
        opc = el.find("./transform/opacity")

        cx, cy = w / 2.0, h / 2.0
        if loc is not None and loc.get("value"):
            xy = loc.get("value").split(",")
            if len(xy) >= 2:
                try:
                    cx, cy = float(xy[0]), float(xy[1])
                except ValueError:
                    pass

        sx, sy = 1.0, 1.0
        if scl is not None and scl.get("value"):
            s = scl.get("value").split(",")
            if len(s) >= 2:
                try:
                    sx, sy = float(s[0]), float(s[1])
                except ValueError:
                    pass

        rotation_deg = 0.0
        if rot is not None and rot.get("value"):
            try:
                rotation_deg = float(rot.get("value"))
            except ValueError:
                pass

        opacity_val = 0.9
        if opc is not None and opc.get("value"):
            try:
                opacity_val = max(0.0, min(1.0, float(opc.get("value"))))
            except ValueError:
                pass

        # Size extraction
        size_el = el.find("./property[@name='size']")
        sw, sh = 120.0, 120.0
        if size_el is not None and size_el.get("value"):
            sz = size_el.get("value").split(",")
            if len(sz) >= 2:
                try:
                    sw, sh = float(sz[0]), float(sz[1])
                except ValueError:
                    pass

        bw, bh = abs(sw * sx), abs(sh * sy)
        if bw <= 0:
            bw = 40.0
        if bh <= 0:
            bh = 40.0
        
        x, y = cx - bw / 2.0, cy - bh / 2.0

        # Build transform attribute for group wrapper
        tf_attrs = []
        if rotation_deg != 0.0:
            tf_attrs.append(f"rotate({rotation_deg} {cx} {cy})")
        tf_str = f' transform="{" ".join(tf_attrs)}"' if tf_attrs else ""

        # Extract effects
        effects = el.findall("./effect")
        eff_names = [e.get("id", "").split(".")[-1] for e in effects if e.get("id")]
        eff_tooltip = f" | Effects: {', '.join(eff_names)}" if eff_names else ""

        parts.append(f'<g id="{layer_id}" class="am-layer-node" data-layer-id="{layer_id}" data-type="{el.tag}"{tf_str}>')
        parts.append(f'<title>{label_esc} ({el.tag}){eff_tooltip}</title>')

        # Render shape based on type
        if fill_type == "media" or el.get("fillImage") or el.get("fillVideo"):
            media_ref = el.get("fillImage") or el.get("fillVideo") or ""
            media_clean = html.escape(media_ref.replace("amproj:", ""))
            parts.append(
                f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="8" '
                f'fill="#1e293b" stroke="#3b82f6" stroke-width="3" stroke-dasharray="10 6" opacity="{opacity_val}"/>'
            )
            font_size = max(14.0, min(bw, bh) / 10.0)
            parts.append(
                f'<text x="{cx}" y="{cy}" fill="#93c5fd" font-size="{font_size}" font-family="sans-serif" font-weight="600" '
                f'text-anchor="middle" dominant-baseline="middle">🎬 {media_clean or "[Media Asset]"}</text>'
            )
        elif el.tag == "embedScene":
            parts.append(
                f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="12" '
                f'fill="rgba(88, 28, 135, 0.4)" stroke="#a855f7" stroke-width="3" opacity="{opacity_val}"/>'
            )
            parts.append(
                f'<text x="{cx}" y="{cy}" fill="#e9d5ff" font-size="20" font-family="sans-serif" font-weight="700" '
                f'text-anchor="middle" dominant-baseline="middle">📦 {label_esc}</text>'
            )
            sub_scene = el.find("./scene")
            if sub_scene is not None:
                for child in list(sub_scene):
                    process_element(child, depth + 1)
        elif el.tag == "text":
            text_content = el.get("text") or el.findtext("./text") or label
            text_esc = html.escape(text_content)
            fill_color = am_color_to_hex(el.findtext("./fillColor") or "#ffffff", "#ffffff")
            font_size = max(16.0, bh * 0.7)
            parts.append(
                f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="6" '
                f'fill="rgba(245, 158, 11, 0.15)" stroke="#f59e0b" stroke-width="2" stroke-dasharray="6 4" opacity="0.6"/>'
            )
            parts.append(
                f'<text x="{cx}" y="{cy}" fill="{fill_color}" font-size="{font_size}" font-family="sans-serif" font-weight="600" '
                f'text-anchor="middle" dominant-baseline="middle">🔤 {text_esc}</text>'
            )
        else:
            # Regular vector shape (rectangle, roundrect, circle/ellipse, polygon)
            fill_el = el.find("./fillColor")
            fill_val = fill_el.get("value") if fill_el is not None else None
            fill_color = am_color_to_hex(fill_val, "#334155")
            rx = 24 if "roundrect" in shape_kind else 0

            if "circle" in shape_kind or "ellipse" in shape_kind:
                parts.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{bw/2.0}" ry="{bh/2.0}" fill="{fill_color}" opacity="{opacity_val}"/>')
            else:
                parts.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="{rx}" fill="{fill_color}" opacity="{opacity_val}"/>')

        parts.append('</g>')

    for el in list(scene):
        process_element(el)

    parts.append("</svg>")
    return "".join(parts)


def render_layer_tree(scene: ET.Element, depth: int = 0) -> List[Dict[str, Any]]:
    """
    Builds a JSON-serializable hierarchical structure of layers.
    """
    tree: List[Dict[str, Any]] = []
    
    # Process top-level media declarations
    for m in scene.findall("./media"):
        tree.append({
            "id": f"media-{m.get('id', '')}",
            "tag": "media",
            "type_label": "Media Asset",
            "label": m.get("filename", "Untitled Asset"),
            "filename": m.get("filename", ""),
            "depth": depth,
            "category": "media",
            "effects": [],
            "dimensions": f"{m.get('width', '?')}×{m.get('height', '?')}",
            "children": [],
        })

    layer_counter = 0

    def traverse(el: ET.Element, current_depth: int) -> Optional[Dict[str, Any]]:
        nonlocal layer_counter
        if el.tag not in ("shape", "embedScene", "text", "audio", "group"):
            return None

        layer_counter += 1
        node_id = f"layer-{layer_counter}"
        label = el.get("label") or el.tag
        shape_kind = el.get("s", "")
        fill_type = el.get("fillType", "")

        # Categorize
        if el.tag == "embedScene":
            cat = "embed"
            type_label = "Embed Scene"
        elif fill_type == "media" or el.get("fillImage") or el.get("fillVideo"):
            cat = "media_layer"
            type_label = "Media Shape"
        elif el.tag == "text":
            cat = "text"
            type_label = "Text Layer"
        elif el.tag == "audio":
            cat = "audio"
            type_label = "Audio Track"
        else:
            cat = "shape"
            type_label = "Vector Shape"

        # Effects
        effects = el.findall("./effect")
        eff_list = []
        for e in effects:
            raw_id = e.get("id", "")
            if raw_id:
                eff_name = raw_id.split(".")[-1]
                eff_name = re.sub(r"([a-z])([A-Z])", r"\1 \2", eff_name).title()
                eff_list.append(eff_name)

        children = []
        if el.tag == "embedScene":
            sub = el.find("./scene")
            if sub is not None:
                for child in list(sub):
                    child_node = traverse(child, current_depth + 1)
                    if child_node:
                        children.append(child_node)

        return {
            "id": node_id,
            "tag": el.tag,
            "type_label": type_label,
            "label": label,
            "depth": current_depth,
            "category": cat,
            "shape_kind": shape_kind,
            "fill_type": fill_type,
            "effects": eff_list,
            "children": children,
        }

    for el in list(scene):
        node = traverse(el, depth)
        if node:
            tree.append(node)

    return tree


def render_tree_html(scene: ET.Element, depth: int = 0) -> str:
    """
    Renders structured HTML layer hierarchy with interactive highlights and badges.
    """
    tree = render_layer_tree(scene, depth)
    if not tree:
        return '<div class="empty-layers">No layers found in scene.</div>'

    html_parts = ['<ul class="am-layer-tree">']

    def render_node(node: Dict[str, Any]):
        cat = node.get("category", "shape")
        node_id = node.get("id", "")
        depth_val = node.get("depth", 0)
        label = html.escape(str(node.get("label", "")))
        type_label = html.escape(str(node.get("type_label", node.get("tag", ""))))
        effects = node.get("effects", [])

        # Icon per category
        icon_map = {
            "media": "🖼️",
            "media_layer": "🎬",
            "embed": "📦",
            "text": "🔤",
            "audio": "🎵",
            "shape": "🔷",
        }
        icon = icon_map.get(cat, "🔹")

        # Effect badges
        eff_html = ""
        if effects:
            badges = "".join(f'<span class="fx-badge">{html.escape(eff)}</span>' for eff in effects)
            eff_html = f'<div class="node-fx-row">{badges}</div>'

        # Meta info
        meta_html = f'<span class="node-tag tag-{cat}">{icon} {type_label}</span>'
        if node.get("dimensions"):
            meta_html += f'<span class="node-meta">{html.escape(str(node["dimensions"]))}</span>'

        children = node.get("children", [])
        has_children = len(children) > 0
        expand_btn = '<button class="tree-toggle" title="Toggle Child Layers">▼</button>' if has_children else ''

        html_parts.append(
            f'<li class="tree-node node-{cat}" data-layer-id="{node_id}" style="--depth: {depth_val}">'
            f'  <div class="node-item">'
            f'    {expand_btn}'
            f'    <span class="node-title">{label}</span>'
            f'    <div class="node-info-right">{meta_html}</div>'
            f'  </div>'
            f'  {eff_html}'
        )

        if has_children:
            html_parts.append('<ul class="tree-subtree">')
            for child in children:
                render_node(child)
            html_parts.append('</ul>')

        html_parts.append('</li>')

    for node in tree:
        render_node(node)

    html_parts.append('</ul>')
    return "".join(html_parts)
