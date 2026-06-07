# Alight Motion Share to XML Extractor

A standalone Python script to extract internal project XML and assets from an Alight Motion share link. This script bypasses the app's standard import process by querying the underlying Firebase Storage endpoints directly, grabbing the `projectfiles.zip`, and parsing out the XML and media.

## Requirements
- Python 3.7+
- No external dependencies (uses purely the Python Standard Library)

## Usage

```bash
# Basic extraction to XML
python am_share_to_xml.py "https://alightcreative.com/am/share/u/cSRKE4GLtKT7GayBmNth6HXsyjz2/p/RNP1b8PlJR-6a4e8d2307e72b4a" -o out.xml

# Download the full project ZIP (XML + Media)
python am_share_to_xml.py <link> --save-zip project.zip

# Extract everything (XML + Media) into a folder
python am_share_to_xml.py <link> --extract-all out_dir/
```

## How it works
Alight Motion stores project packages publicly on Firebase Storage (`alight-creative.appspot.com`).
The script parses the `user_id` and `package_id` from the URL, constructs the Firebase Storage REST API path, downloads the raw ZIP buffer, and extracts the target artifacts in memory.
