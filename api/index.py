import os
import sys
import urllib.parse
from flask import Flask, request, Response, render_template, jsonify

# Add workspace root to Python path so `core` can be imported anywhere
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.extractor import (
    fetch_package,
    extract_package_contents,
    extract_xml_from_zip,
    extract_single_file,
    ExtractorError,
    InvalidShareLinkError,
    StorageDownloadError,
    PackageCorruptedError,
)
from core.parser import (
    parse_xml_string,
    parse_scene_metadata,
    beautify_xml,
)
from core.renderer import (
    render_svg,
    render_layer_tree,
    render_tree_html,
)

# Initialize Flask application with explicit templates & static paths
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
    static_url_path="/static",
)


@app.route("/", methods=["GET"])
def home():
    """Renders the main modern extractor landing page."""
    return render_template("index.html", active_page="home")


@app.route("/batch", methods=["GET"])
def batch_page():
    """Renders the batch links processing page."""
    return render_template("batch.html", active_page="batch")


@app.route("/extract", methods=["GET"])
def extract():
    """
    Downloads package and returns attachment file (Full ZIP, Raw XML, or Beautified XML).
    """
    link = request.args.get("url", "").strip()
    if not link:
        return "Missing 'url' query parameter.", 400

    mode = request.args.get("mode", "full").strip().lower()

    try:
        user_id, package_id, zip_bytes = fetch_package(link)
    except ExtractorError as e:
        return str(e), e.status_code
    except Exception as e:
        return f"Internal extractor error: {e}", 500

    if mode in ("xml", "beautify"):
        try:
            xml_name, xml_bytes = extract_xml_from_zip(zip_bytes)
            
            if mode == "beautify":
                beautified = beautify_xml(xml_bytes)
                output_bytes = beautified.encode("utf-8")
            else:
                output_bytes = xml_bytes

            return Response(
                output_bytes,
                mimetype="application/xml; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="{package_id}.xml"'
                },
            )
        except Exception as e:
            return f"Error extracting XML from archive: {e}", 500

    # Default: Full project archive (.zip)
    return Response(
        zip_bytes,
        mimetype="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{package_id}.zip"'
        },
    )


@app.route("/preview", methods=["GET"])
def preview():
    """
    Renders the interactive Studio Preview workspace.
    """
    link = request.args.get("url", "").strip()
    if not link:
        return render_template("index.html", error="Please provide a valid share link."), 400

    try:
        user_id, package_id, zip_bytes = fetch_package(link)
        pkg_data = extract_package_contents(zip_bytes)
        
        scene_el = parse_xml_string(pkg_data["xml_bytes"])
        metadata = parse_scene_metadata(scene_el, package_id)
        
        svg_markup = render_svg(scene_el)
        layer_tree_html = render_tree_html(scene_el)
        pretty_xml = beautify_xml(pkg_data["xml_bytes"])

        return render_template(
            "preview.html",
            raw_url=link,
            user_id=user_id,
            package_id=package_id,
            metadata=metadata,
            package=pkg_data,
            svg_markup=svg_markup,
            layer_tree_html=layer_tree_html,
            pretty_xml=pretty_xml,
        )
    except ExtractorError as e:
        return f"""
        <div style="background:#09090b;color:#f8fafc;font-family:sans-serif;padding:40px;text-align:center;">
            <h2 style="color:#f43f5e;margin-bottom:12px;">Extraction Failed</h2>
            <p style="color:#94a3b8;margin-bottom:24px;">{e.message}</p>
            <a href="/" style="background:#3b82f6;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;">← Return Home</a>
        </div>
        """, e.status_code
    except Exception as e:
        return f"""
        <div style="background:#09090b;color:#f8fafc;font-family:sans-serif;padding:40px;text-align:center;">
            <h2 style="color:#f43f5e;margin-bottom:12px;">Error Analyzing Scene</h2>
            <p style="color:#94a3b8;margin-bottom:24px;">{e}</p>
            <a href="/" style="background:#3b82f6;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;">← Return Home</a>
        </div>
        """, 500


@app.route("/api/info", methods=["GET"])
def api_info():
    """
    REST API endpoint: Returns comprehensive metadata, layer structure,
    asset manifest, and rendered SVG in JSON format.
    """
    link = request.args.get("url", "").strip()
    if not link:
        return jsonify({"success": False, "error": "Missing 'url' query parameter."}), 400

    try:
        user_id, package_id, zip_bytes = fetch_package(link)
        pkg_data = extract_package_contents(zip_bytes)
        
        scene_el = parse_xml_string(pkg_data["xml_bytes"])
        metadata = parse_scene_metadata(scene_el, package_id)
        layer_tree = render_layer_tree(scene_el)
        svg_preview = render_svg(scene_el)

        return jsonify({
            "success": true_or_bool(True),
            "user_id": user_id,
            "package_id": package_id,
            "metadata": metadata,
            "package": {
                "xml_name": pkg_data["xml_name"],
                "manifest_name": pkg_data["manifest_name"],
                "manifest_text": pkg_data["manifest_text"],
                "media_count": pkg_data["media_count"],
                "media_files": pkg_data["media_files"],
                "total_files_count": pkg_data["total_files_count"],
                "total_uncompressed_formatted": pkg_data["total_uncompressed_formatted"],
            },
            "layer_tree": layer_tree,
            "svg_preview": svg_preview,
        })
    except ExtractorError as e:
        return jsonify({"success": False, "error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/asset", methods=["GET"])
def api_asset():
    """
    REST API endpoint: Stream or download an individual media asset from the package.
    """
    link = request.args.get("url", "").strip()
    filename = request.args.get("file", "").strip()

    if not link or not filename:
        return "Missing 'url' or 'file' parameter.", 400

    try:
        user_id, package_id, zip_bytes = fetch_package(link)
        matched_fn, file_bytes, mime_type = extract_single_file(zip_bytes, filename)
        
        basename = matched_fn.split("/")[-1]
        return Response(
            file_bytes,
            mimetype=mime_type,
            headers={
                "Content-Disposition": f'inline; filename="{basename}"'
            },
        )
    except ExtractorError as e:
        return str(e), e.status_code
    except Exception as e:
        return f"Error extracting asset: {e}", 500


@app.route("/api/batch", methods=["POST"])
def api_batch():
    """
    REST API endpoint: Inspect multiple URLs concurrently or sequentially.
    """
    data = request.get_json(silent=True) or {}
    urls = data.get("urls", [])
    if not isinstance(urls, list) or not urls:
        return jsonify({"success": False, "error": "Provide an array of URLs in 'urls' field."}), 400

    results = []
    for link in urls[:20]:  # Limit max 20 per request
        link = link.strip()
        if not link:
            continue
        try:
            user_id, package_id, zip_bytes = fetch_package(link)
            pkg_data = extract_package_contents(zip_bytes)
            scene_el = parse_xml_string(pkg_data["xml_bytes"])
            metadata = parse_scene_metadata(scene_el, package_id)
            results.append({
                "url": link,
                "success": True,
                "user_id": user_id,
                "package_id": package_id,
                "metadata": metadata,
                "media_count": pkg_data["media_count"],
            })
        except Exception as e:
            results.append({
                "url": link,
                "success": False,
                "error": str(e),
            })

    return jsonify({"success": True, "results": results, "total": len(results)})


def true_or_bool(val):
    return bool(val)


if __name__ == "__main__":
    # Local development server
    port = int(os.environ.get("PORT", 5000))
    print(f"[*] Starting Nexus Alight Extractor server on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
