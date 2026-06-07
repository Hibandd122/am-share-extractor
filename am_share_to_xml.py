"""
Alight Motion share-link -> XML extractor

Cách hoạt động (rút ra từ phân tích AlightMotion.app binary trong IPA):

  Share link:
    https://alightcreative.com/am/share/u/<USER_ID>/p/<PACKAGE_ID>

  Project package được lưu công khai trên Firebase Storage:
    bucket: alight-creative.appspot.com
    object: share/u/<USER_ID>/p/<PACKAGE_ID>/projectfiles.zip

  -> Tải zip qua endpoint Firebase REST:
       https://firebasestorage.googleapis.com/v0/b/<BUCKET>/o/<URL-ENCODED-PATH>?alt=media

  Bên trong projectfiles.zip có:
    - <uuid>.xml        <-- file scene XML (cái mình cần)
    - manifest.txt      <-- danh sách media + SHA1
    - các file media (mp4, jpg, ...)

Usage:
    python am_share_to_xml.py "https://alightcreative.com/am/share/u/.../p/..."
    python am_share_to_xml.py <link> -o out.xml
    python am_share_to_xml.py <link> --save-zip pkg.zip
    python am_share_to_xml.py <link> --extract-all out_dir/
"""

import argparse
import io
import os
import re
import sys
import urllib.parse
import urllib.request
import zipfile

FIREBASE_BUCKET = "alight-creative.appspot.com"
FIREBASE_HOST = "https://firebasestorage.googleapis.com"

SHARE_LINK_RE = re.compile(
    r"alightcreative\.com/am/share/u/(?P<user>[A-Za-z0-9_-]+)/p/(?P<package>[A-Za-z0-9_\-]+)",
    re.IGNORECASE,
)


def parse_share_link(link: str):
    m = SHARE_LINK_RE.search(link)
    if not m:
        raise ValueError(f"Không nhận diện được share link Alight Motion: {link!r}")
    return m.group("user"), m.group("package")


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


def extract_xml_from_zip(zip_bytes: bytes) -> tuple[str, bytes]:
    """Trả về (tên file xml, nội dung xml). Raise nếu không tìm thấy."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        xml_names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if not xml_names:
            raise RuntimeError(
                f"Không có file .xml trong package. Có: {zf.namelist()}"
            )
        # Thường chỉ có 1 file .xml (<uuid>.xml) - lấy file lớn nhất nếu nhiều
        xml_names.sort(key=lambda n: zf.getinfo(n).file_size, reverse=True)
        name = xml_names[0]
        return name, zf.read(name)


def extract_all(zip_bytes: bytes, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(out_dir)
        return zf.namelist()


def main():
    p = argparse.ArgumentParser(
        description="Convert Alight Motion share link to project XML"
    )
    p.add_argument("link", help="Share link Alight Motion")
    p.add_argument(
        "-o", "--output",
        help="File XML output (mặc định: <package_id>.xml ngay tại thư mục hiện hành)",
    )
    p.add_argument(
        "--save-zip",
        help="Lưu cả file projectfiles.zip ra đường dẫn này",
    )
    p.add_argument(
        "--extract-all",
        metavar="DIR",
        help="Giải nén toàn bộ projectfiles.zip vào thư mục này (gồm media)",
    )
    p.add_argument(
        "-q", "--quiet", action="store_true", help="Bớt log"
    )
    args = p.parse_args()

    def log(*a):
        if not args.quiet:
            print(*a, file=sys.stderr)

    user_id, package_id = parse_share_link(args.link)
    log(f"[*] user    = {user_id}")
    log(f"[*] package = {package_id}")

    url = build_storage_url(user_id, package_id)
    log(f"[*] download: {url}")

    try:
        zip_bytes = download(url)
    except urllib.error.HTTPError as e:
        print(f"[!] HTTP {e.code}: {e.reason}", file=sys.stderr)
        print(f"[!] URL: {url}", file=sys.stderr)
        # Thử các filename khác phòng khi project được lưu khác
        for alt in ("projectFiles.zip", "package.zip"):
            alt_url = build_storage_url(user_id, package_id, alt)
            try:
                zip_bytes = download(alt_url)
                log(f"[*] dùng fallback: {alt_url}")
                break
            except urllib.error.HTTPError:
                continue
        else:
            sys.exit(2)

    log(f"[*] tải xong {len(zip_bytes):,} byte")

    if args.save_zip:
        with open(args.save_zip, "wb") as f:
            f.write(zip_bytes)
        log(f"[*] đã lưu zip: {args.save_zip}")

    if args.extract_all:
        names = extract_all(zip_bytes, args.extract_all)
        log(f"[*] đã giải nén {len(names)} file vào {args.extract_all}")
        for n in names:
            log(f"      - {n}")

    xml_name, xml_bytes = extract_xml_from_zip(zip_bytes)
    log(f"[*] xml trong zip: {xml_name} ({len(xml_bytes):,} byte)")

    out_path = args.output or f"{package_id}.xml"
    with open(out_path, "wb") as f:
        f.write(xml_bytes)
    log(f"[+] đã lưu XML: {out_path}")
    print(out_path)


if __name__ == "__main__":
    main()
