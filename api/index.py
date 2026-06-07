from flask import Flask, request, Response, render_template_string
import io
import urllib.parse
import urllib.request
import zipfile
import re

app = Flask(__name__)

FIREBASE_BUCKET = "alight-creative.appspot.com"
FIREBASE_HOST = "https://firebasestorage.googleapis.com"
SHARE_LINK_RE = re.compile(
    r"alightcreative\.com/am/share/u/(?P<user>[A-Za-z0-9_-]+)/p/(?P<package>[A-Za-z0-9_\-]+)",
    re.IGNORECASE,
)

def build_storage_url(user_id: str, package_id: str, filename: str = "projectfiles.zip") -> str:
    object_path = f"share/u/{user_id}/p/{package_id}/{filename}"
    encoded = urllib.parse.quote(object_path, safe="")
    return f"{FIREBASE_HOST}/v0/b/{FIREBASE_BUCKET}/o/{encoded}?alt=media"

def download(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AlightMotion/6.2.53 (iOS)",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()

def extract_xml_from_zip(zip_bytes: bytes) -> tuple:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        xml_names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if not xml_names:
            raise RuntimeError("No .xml file found inside the package.")
        xml_names.sort(key=lambda n: zf.getinfo(n).file_size, reverse=True)
        name = xml_names[0]
        return name, zf.read(name)

@app.route("/", methods=["GET"])
def index():
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Alight Motion XML Extractor</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    background-color: #f0f2f5;
                    color: #333;
                    max-width: 600px;
                    margin: 40px auto;
                    padding: 20px;
                }
                .container {
                    background: #fff;
                    padding: 30px;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                h2 { margin-top: 0; color: #1a1a1a; }
                p { color: #555; line-height: 1.5; }
                input[type=text] {
                    width: 100%;
                    padding: 12px;
                    margin: 15px 0;
                    border: 1px solid #ccc;
                    border-radius: 6px;
                    box-sizing: border-box;
                    font-size: 16px;
                }
                button {
                    width: 100%;
                    padding: 12px;
                    background: #0070f3;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: bold;
                    cursor: pointer;
                    transition: background 0.2s;
                }
                button:hover { background: #0051b3; }
                .footer { margin-top: 20px; text-align: center; font-size: 12px; color: #888; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>AM XML Extractor</h2>
                <p>Paste your Alight Motion share link below to directly download the internal project XML.</p>
                <form action="/extract" method="GET">
                    <input type="text" name="url" placeholder="https://alightcreative.com/am/share/u/..." required />
                    <button type="submit">Download XML</button>
                </form>
            </div>
            <div class="footer">
                Powered by Python & Flask
            </div>
        </body>
        </html>
    ''')

@app.route("/extract", methods=["GET"])
def extract():
    link = request.args.get("url", "").strip()
    if not link:
        return "Missing url parameter", 400
    
    m = SHARE_LINK_RE.search(link)
    if not m:
        return "Invalid Alight Motion share link format.", 400
    
    user_id = m.group("user")
    package_id = m.group("package")
    
    url = build_storage_url(user_id, package_id)
    zip_bytes = None
    
    try:
        zip_bytes = download(url)
    except Exception as e:
        # Fallback names
        for alt in ("projectFiles.zip", "package.zip"):
            alt_url = build_storage_url(user_id, package_id, alt)
            try:
                zip_bytes = download(alt_url)
                break
            except:
                pass
                
    if not zip_bytes:
        return "Failed to download project package from Firebase Storage. The link might be expired or invalid.", 404
        
    try:
        xml_name, xml_bytes = extract_xml_from_zip(zip_bytes)
        return Response(
            xml_bytes,
            mimetype="application/xml",
            headers={
                "Content-Disposition": f'attachment; filename="{package_id}.xml"'
            }
        )
    except Exception as e:
        return f"Error parsing ZIP or extracting XML: {e}", 500

if __name__ == "__main__":
    app.run(debug=True)
