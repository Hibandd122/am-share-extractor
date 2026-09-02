#!/usr/bin/env python3
"""
Nexus Alight Motion Share to XML & Assets Extractor CLI
"""

import argparse
import json
import os
import sys

# Ensure local core package is discoverable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.extractor import (
    fetch_package,
    extract_xml_from_zip,
    extract_package_contents,
    ExtractorError,
)
from core.parser import (
    parse_xml_string,
    parse_scene_metadata,
    beautify_xml,
)


def main():
    parser = argparse.ArgumentParser(
        description="Extract XML project definitions, layer hierarchy, and media assets from Alight Motion share links."
    )
    parser.add_argument("link", help="Alight Motion share link (e.g. https://alightcreative.com/am/share/u/.../p/...)")
    parser.add_argument(
        "-o", "--output",
        help="Path to save output XML file (default: <package_id>.xml)",
    )
    parser.add_argument(
        "--beautify", action="store_true",
        help="Format and indent XML with clean line breaks",
    )
    parser.add_argument(
        "--save-zip", metavar="ZIP_PATH",
        help="Save raw project ZIP package (XML + Media) to this file path",
    )
    parser.add_argument(
        "--extract-all", metavar="DIR",
        help="Extract all package contents (XML + all media assets) into directory",
    )
    parser.add_argument(
        "--extract-media", metavar="DIR",
        help="Extract only media assets (images, videos, audio) into directory",
    )
    parser.add_argument(
        "--info", action="store_true",
        help="Display detailed project specifications and layer metadata",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output project metadata as JSON to stdout",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="Suppress status and progress messages",
    )

    args = parser.parse_args()

    def log(msg: str):
        if not args.quiet and not args.json:
            print(msg, file=sys.stderr)

    try:
        log("[*] Connecting to Firebase Storage...")
        user_id, package_id, zip_bytes = fetch_package(args.link)
        log(f"[+] Downloaded package: {package_id} ({len(zip_bytes):,} bytes)")

        pkg_data = extract_package_contents(zip_bytes)
        scene_el = parse_xml_string(pkg_data["xml_bytes"])
        metadata = parse_scene_metadata(scene_el, package_id)

        # JSON Mode
        if args.json:
            out = {
                "user_id": user_id,
                "package_id": package_id,
                "metadata": metadata,
                "files_count": pkg_data["total_files_count"],
                "media_count": pkg_data["media_count"],
                "media_files": pkg_data["media_files"],
            }
            print(json.dumps(out, indent=2))
            return

        # Info Mode
        if args.info:
            print("=" * 60)
            print(f"🎬 ALIGHT MOTION PROJECT SPECIFICATIONS")
            print("=" * 60)
            print(f"Title:         {metadata['title']}")
            print(f"Package ID:    {package_id}")
            print(f"User ID:       {user_id}")
            print(f"Resolution:    {metadata['resolution']} ({metadata['aspect_ratio']})")
            print(f"Framerate:     {metadata['fps']} FPS")
            print(f"Duration:      {metadata['duration_formatted']} ({metadata['duration_sec']}s)")
            print(f"Background:    {metadata['bgcolor_raw']} -> {metadata['bgcolor_css']}")
            print(f"Total Layers:  {metadata['total_layers']} (Shapes: {metadata['shapes_count']}, Scenes: {metadata['embed_scenes_count']}, Text: {metadata['text_count']})")
            print(f"Media Assets:  {pkg_data['media_count']} files")
            if metadata["fonts_used"]:
                print(f"Fonts Used:    {', '.join(metadata['fonts_used'])}")
            if metadata["effects_used"]:
                print(f"Effects:       {', '.join(metadata['effects_used'])}")
            print("=" * 60)

        # Save Full ZIP
        if args.save_zip:
            with open(args.save_zip, "wb") as f:
                f.write(zip_bytes)
            log(f"[+] Saved project ZIP: {args.save_zip}")

        # Extract All Contents
        if args.extract_all:
            import zipfile
            import io
            os.makedirs(args.extract_all, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                zf.extractall(args.extract_all)
            log(f"[+] Extracted all {len(pkg_data['all_files'])} files into: {args.extract_all}")

        # Extract Media Only
        if args.extract_media:
            import zipfile
            import io
            os.makedirs(args.extract_media, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                extracted_media = 0
                for item in pkg_data["media_files"]:
                    fn = item["filename"]
                    zf.extract(fn, args.extract_media)
                    extracted_media += 1
            log(f"[+] Extracted {extracted_media} media assets into: {args.extract_media}")

        # Save XML (default or explicit -o)
        if not args.info or args.output:
            xml_bytes = pkg_data["xml_bytes"]
            if args.beautify:
                pretty = beautify_xml(xml_bytes)
                xml_bytes = pretty.encode("utf-8")

            out_path = args.output or f"{package_id}.xml"
            with open(out_path, "wb") as f:
                f.write(xml_bytes)
            log(f"[+] Saved project XML: {out_path} ({len(xml_bytes):,} bytes)")
            if not args.json and not args.info:
                print(out_path)

    except ExtractorError as e:
        print(f"[!] Extractor Error: {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[!] Unexpected Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
