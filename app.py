import os
import sys

# Ensure root & api directories are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
API_DIR = os.path.join(BASE_DIR, "api")
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from api.index import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
