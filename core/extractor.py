import io
import mimetypes
import re
import urllib.parse
import urllib.request
import zipfile
from typing import Dict, List, Optional, Tuple, Any

FIREBASE_BUCKET = "alight-creative.appspot.com"
FIREBASE_HOST = "https://firebasestorage.googleapis.com"

# Regular expression to match various Alight Motion share link formats
SHARE_LINK_RE = re.compile(
    r"(?:alightcreative\.com|alight\.link)/am/share/u/(?P<user>[A-Za-z0-9_-]+)/p/(?P<package>[A-Za-z0-9_\-]+)",
    re.IGNORECASE,
)

# Common package filenames in Firebase Storage
FALLBACK_FILENAMES = (
    "projectfiles.zip",
    "projectFiles.zip",
    "package.zip",
    "project.zip",
)

USER_AGENT = "AlightMotion/6.2.53 (iOS; gzip)"


class ExtractorError(Exception):
    """Base exception for extractor errors."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class InvalidShareLinkError(ExtractorError):
    def __init__(self, message: str = "Invalid Alight Motion share link format."):
        super().__init__(message, 400)


class StorageDownloadError(ExtractorError):
    def __init__(self, message: str = "Failed to download project package from Firebase Storage. The link might be expired or deleted."):
        super().__init__(message, 404)


class PackageCorruptedError(ExtractorError):
    def __init__(self, message: str = "Corrupted ZIP package or missing XML scene definition."):
        super().__init__(message, 500)


def parse_share_link(link: str) -> Tuple[str, str]:
    """
    Extracts user_id and package_id from an Alight Motion share URL.
    Raises InvalidShareLinkError if the format is invalid.
    """
    if not link:
        raise InvalidShareLinkError("Empty share link provided.")
    
    clean_link = link.strip()
    match = SHARE_LINK_RE.search(clean_link)
    if not match:
        raise InvalidShareLinkError(
            f"Cannot parse Alight Motion share link: '{clean_link}'. "
            "Expected format: https://alightcreative.com/am/share/u/{USER}/p/{PACKAGE}"
        )
    return match.group("user"), match.group("package")


def build_storage_url(user_id: str, package_id: str, filename: str = "projectfiles.zip") -> str:
    """
    Constructs the Firebase Storage REST API download URL.
    """
    object_path = f"share/u/{user_id}/p/{package_id}/{filename}"
    encoded_path = urllib.parse.quote(object_path, safe="")
    return f"{FIREBASE_HOST}/v0/b/{FIREBASE_BUCKET}/o/{encoded_path}?alt=media"


def download(url: str, timeout: int = 120) -> bytes:
    """
    Downloads raw binary data from URL with custom iOS client headers.
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_package(link: str) -> Tuple[str, str, bytes]:
    """
    Parses share link and downloads projectfiles.zip using fallback filenames.
    Returns: (user_id, package_id, zip_bytes)
    Raises: InvalidShareLinkError, StorageDownloadError
    """
    user_id, package_id = parse_share_link(link)
    zip_bytes = None
    last_err = None

    for name in FALLBACK_FILENAMES:
        storage_url = build_storage_url(user_id, package_id, name)
        try:
            zip_bytes = download(storage_url)
            if zip_bytes and len(zip_bytes) > 0:
                break
        except Exception as e:
            last_err = e
            continue

    if not zip_bytes:
        raise StorageDownloadError(
            f"Failed to download project package for package ID '{package_id}'. "
            f"Storage endpoints returned not found or inaccessible. ({last_err})"
        )

    return user_id, package_id, zip_bytes


def extract_xml_from_zip(zip_bytes: bytes) -> Tuple[str, bytes]:
    """
    Extracts the main project XML scene from the ZIP package.
    Returns: (xml_filename, xml_bytes)
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            xml_names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
            if not xml_names:
                raise PackageCorruptedError("No .xml scene descriptor found inside the ZIP package.")
            # Take the largest XML file if multiple exist (usually <uuid>.xml)
            xml_names.sort(key=lambda n: zf.getinfo(n).file_size, reverse=True)
            chosen = xml_names[0]
            return chosen, zf.read(chosen)
    except zipfile.BadZipFile:
        raise PackageCorruptedError("The downloaded binary payload is not a valid ZIP archive.")


def extract_package_contents(zip_bytes: bytes) -> Dict[str, Any]:
    """
    Analyzes the entire ZIP package and returns structured information:
    - xml_name, xml_bytes
    - manifest_name, manifest_text
    - media_files: list of dicts with file metadata
    - all_files: list of all entries in zip
    - total_size: total uncompressed size in bytes
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            infolist = zf.infolist()
            xml_name, xml_bytes = None, b""
            manifest_name, manifest_text = None, ""
            media_files: List[Dict[str, Any]] = []
            all_files: List[Dict[str, Any]] = []
            total_uncompressed = 0

            # Find XML
            xml_candidates = [info for info in infolist if info.filename.lower().endswith(".xml")]
            if xml_candidates:
                xml_candidates.sort(key=lambda info: info.file_size, reverse=True)
                main_xml_info = xml_candidates[0]
                xml_name = main_xml_info.filename
                xml_bytes = zf.read(xml_name)

            for info in infolist:
                fn = info.filename
                f_lower = fn.lower()
                size = info.file_size
                total_uncompressed += size

                # Manifest
                if f_lower in ("manifest.txt", "manifest.json"):
                    manifest_name = fn
                    try:
                        manifest_text = zf.read(fn).decode("utf-8", errors="replace")
                    except Exception:
                        manifest_text = ""

                mime, _ = mimetypes.guess_type(fn)
                mime = mime or "application/octet-stream"
                
                is_img = mime.startswith("image/") or f_lower.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"))
                is_vid = mime.startswith("video/") or f_lower.endswith((".mp4", ".mov", ".m4v", ".webm"))
                is_aud = mime.startswith("audio/") or f_lower.endswith((".mp3", ".m4a", ".wav", ".aac", ".ogg"))
                is_xml = f_lower.endswith(".xml")

                category = "other"
                if is_xml:
                    category = "xml"
                elif is_img:
                    category = "image"
                elif is_vid:
                    category = "video"
                elif is_aud:
                    category = "audio"
                elif "manifest" in f_lower:
                    category = "manifest"

                item = {
                    "filename": fn,
                    "basename": fn.split("/")[-1],
                    "size": size,
                    "size_formatted": format_file_size(size),
                    "mime_type": mime,
                    "category": category,
                    "is_media": is_img or is_vid or is_aud,
                }
                all_files.append(item)

                if is_img or is_vid or is_aud:
                    media_files.append(item)

            if not xml_name or not xml_bytes:
                raise PackageCorruptedError("Project XML was not found inside the ZIP package.")

            return {
                "xml_name": xml_name,
                "xml_bytes": xml_bytes,
                "manifest_name": manifest_name,
                "manifest_text": manifest_text,
                "media_files": media_files,
                "all_files": all_files,
                "total_uncompressed_size": total_uncompressed,
                "total_uncompressed_formatted": format_file_size(total_uncompressed),
                "total_files_count": len(all_files),
                "media_count": len(media_files),
            }
    except zipfile.BadZipFile:
        raise PackageCorruptedError("Invalid or corrupted ZIP package.")


def extract_single_file(zip_bytes: bytes, target_filename: str) -> Tuple[str, bytes, str]:
    """
    Extracts a specific file from the ZIP archive in memory.
    Returns: (filename, file_bytes, mime_type)
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            # Case-insensitive / normalized search
            matched_name = None
            target_norm = target_filename.strip().lower()
            for name in zf.namelist():
                if name.lower() == target_norm or name.split("/")[-1].lower() == target_norm:
                    matched_name = name
                    break

            if not matched_name:
                raise ExtractorError(f"File '{target_filename}' not found inside project package.", 404)

            data = zf.read(matched_name)
            mime, _ = mimetypes.guess_type(matched_name)
            return matched_name, data, mime or "application/octet-stream"
    except zipfile.BadZipFile:
        raise PackageCorruptedError("Invalid ZIP package.")


def format_file_size(num_bytes: int) -> str:
    """Format bytes into readable string (KB, MB, GB)."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"
