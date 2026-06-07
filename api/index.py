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
            <title>Nexus XML Extractor</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
            <style>
                :root {
                    --bg: #09090b;
                    --glass-bg: rgba(255, 255, 255, 0.03);
                    --glass-border: rgba(255, 255, 255, 0.05);
                    --primary: #3b82f6;
                    --primary-glow: rgba(59, 130, 246, 0.4);
                    --accent: #8b5cf6;
                    --text-main: #f8fafc;
                    --text-muted: #94a3b8;
                }

                * {
                    box-sizing: border-box;
                    margin: 0;
                    padding: 0;
                    font-family: 'Outfit', sans-serif;
                }

                body {
                    background-color: var(--bg);
                    color: var(--text-main);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    position: relative;
                    overflow: hidden;
                }

                .orb {
                    position: absolute;
                    border-radius: 50%;
                    filter: blur(80px);
                    opacity: 0.4;
                    animation: float 10s infinite alternate ease-in-out;
                    z-index: 0;
                }
                .orb-1 {
                    width: 400px; height: 400px;
                    background: var(--primary);
                    top: -100px; left: -100px;
                }
                .orb-2 {
                    width: 300px; height: 300px;
                    background: var(--accent);
                    bottom: -50px; right: -50px;
                    animation-delay: -5s;
                }

                @keyframes float {
                    0% { transform: translate(0, 0) scale(1); }
                    100% { transform: translate(30px, 50px) scale(1.1); }
                }

                .container {
                    position: relative;
                    z-index: 1;
                    background: var(--glass-bg);
                    backdrop-filter: blur(20px);
                    -webkit-backdrop-filter: blur(20px);
                    border: 1px solid var(--glass-border);
                    padding: 45px 40px;
                    border-radius: 24px;
                    width: 90%;
                    max-width: 480px;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
                    text-align: center;
                    transform: translateY(20px);
                    opacity: 0;
                    animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
                }

                @keyframes slideUp {
                    to { transform: translateY(0); opacity: 1; }
                }

                h2 {
                    font-size: 32px;
                    font-weight: 800;
                    margin-bottom: 12px;
                    background: linear-gradient(to right, #60a5fa, #c084fc);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    letter-spacing: -0.5px;
                }

                p {
                    color: var(--text-muted);
                    font-size: 15px;
                    margin-bottom: 35px;
                    line-height: 1.6;
                }

                .input-group {
                    position: relative;
                    margin-bottom: 24px;
                    text-align: left;
                }

                input[type="text"] {
                    width: 100%;
                    padding: 16px 20px;
                    background: rgba(0, 0, 0, 0.3);
                    border: 1px solid var(--glass-border);
                    border-radius: 14px;
                    color: white;
                    font-size: 15px;
                    transition: all 0.3s ease;
                    outline: none;
                    letter-spacing: 0.5px;
                }

                input[type="text"]:focus {
                    border-color: rgba(59, 130, 246, 0.5);
                    box-shadow: 0 0 20px var(--primary-glow);
                    background: rgba(0, 0, 0, 0.5);
                }

                input[type="text"]::placeholder {
                    color: #475569;
                }

                button {
                    width: 100%;
                    padding: 16px;
                    background: linear-gradient(135deg, var(--primary), var(--accent));
                    color: white;
                    border: none;
                    border-radius: 14px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    position: relative;
                    overflow: hidden;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                }

                button::after {
                    content: '';
                    position: absolute;
                    top: 0; left: -100%; width: 50%; height: 100%;
                    background: linear-gradient(to right, transparent, rgba(255,255,255,0.2), transparent);
                    transform: skewX(-20deg);
                    transition: all 0.6s ease;
                }

                button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 10px 25px -10px var(--accent);
                }

                button:hover::after {
                    left: 150%;
                }

                button:active {
                    transform: translateY(0);
                }

                .footer {
                    margin-top: 35px;
                    font-size: 11px;
                    color: #334155;
                    font-weight: 600;
                    letter-spacing: 2px;
                    text-transform: uppercase;
                }

                /* Loading State */
                .btn-text { transition: opacity 0.2s; }
                .spinner {
                    position: absolute;
                    top: 50%; left: 50%;
                    transform: translate(-50%, -50%);
                    width: 22px; height: 22px;
                    border: 2px solid rgba(255,255,255,0.3);
                    border-top-color: white;
                    border-radius: 50%;
                    animation: spin 0.8s linear infinite;
                    opacity: 0;
                    transition: opacity 0.2s;
                }
                button.loading .btn-text { opacity: 0; }
                button.loading .spinner { opacity: 1; }
                button.loading { pointer-events: none; opacity: 0.9; }

                @keyframes spin {
                    to { transform: translate(-50%, -50%) rotate(360deg); }
                }
            </style>
        </head>
        <body>
            <div class="orb orb-1"></div>
            <div class="orb orb-2"></div>
            
            <div class="container">
                <h2>Nexus Extractor</h2>
                <p>Bypass Firebase restrictions to extract raw XML payloads from Alight Motion share links.</p>
                
                <form id="extractForm" action="/extract" method="GET">
                    <div class="input-group">
                        <input type="text" id="urlInput" name="url" placeholder="https://alightcreative.com/am/share/u/..." autocomplete="off" required />
                    </div>
                    <button type="submit" id="submitBtn">
                        <span class="btn-text">Extract Payload</span>
                        <div class="spinner"></div>
                    </button>
                </form>
                
                <div class="footer">
                    AUTHORIZED ENGAGEMENT ONLY
                </div>
            </div>

            <script>
                const form = document.getElementById('extractForm');
                const btn = document.getElementById('submitBtn');
                const input = document.getElementById('urlInput');

                form.addEventListener('submit', (e) => {
                    if (input.value.trim() === '') return;
                    btn.classList.add('loading');
                    
                    setTimeout(() => {
                        btn.classList.remove('loading');
                        input.value = '';
                    }, 2500);
                });
            </script>
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
