#!/usr/bin/env python3
"""Rebuild web assets from the supplied PPTX without changing its embedded originals.

Requires Pillow.  The source presentation is deliberately never copied into this
repository.  Every image is resolved through the presentation/slide relationships
and checked against the pre-existing extraction manifest before it is published.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import posixpath
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from PIL import ExifTags, Image, __version__ as pillow_version, features


NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
REL_ID = "{" + NS["r"] + "}id"
REL_EMBED = "{" + NS["r"] + "}embed"
DEFAULT_MANIFEST = Path(r"G:\GithubLocal-PC\rough-as-guts-meeting\review\manifest.json")
DEFAULT_PPTX = Path(r"L:\Downloads after 20_09_22\Rough-as-guts.pptx")
PIPELINE_VERSION = "1.0.0"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relationships(archive: ZipFile, part_path: str) -> dict[str, dict]:
    parent, name = posixpath.split(part_path)
    rel_path = posixpath.join(parent, "_rels", name + ".rels")
    if rel_path not in archive.namelist():
        return {}
    result = {}
    for rel in ET.fromstring(archive.read(rel_path)):
        target = rel.attrib["Target"]
        external = rel.attrib.get("TargetMode") == "External"
        result[rel.attrib["Id"]] = {
            "type": rel.attrib["Type"],
            "external": external,
            "target": target if external else posixpath.normpath(posixpath.join(parent, target)),
        }
    return result


def jpeg_metadata_segments(data: bytes) -> list[tuple[int, bytes]]:
    """Read JPEG header segments only; do not interpret/validate C2PA claims."""
    segments = []
    if not data.startswith(b"\xff\xd8"):
        return segments
    offset = 2
    while offset < len(data):
        if data[offset] != 0xFF:
            break
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in (0xDA, 0xD9):  # start of scan / end of image
            break
        if marker in (0x00, 0x01) or 0xD0 <= marker <= 0xD8:
            continue
        if offset + 2 > len(data):
            break
        length = int.from_bytes(data[offset:offset + 2], "big")
        if length < 2 or offset + length > len(data):
            break
        segments.append((marker, data[offset + 2:offset + length]))
        offset += length
    return segments


def image_metadata(data: bytes, image: Image.Image) -> dict:
    segments = jpeg_metadata_segments(data)
    app11 = [payload for marker, payload in segments if marker == 0xEB]
    exif_raw = [payload for marker, payload in segments
                if marker == 0xE1 and payload.startswith(b"Exif\x00\x00")]
    exif = image.getexif()
    c2pa_found = any(b"c2pa" in payload.lower() for payload in app11)
    jumbf_found = any(b"jumb" in payload for payload in app11)
    selected_exif = {}
    useful_tags = {"Artist", "Copyright", "Software", "ImageDescription", "Make", "Model", "DateTime", "Orientation"}
    for tag, value in exif.items():
        tag_name = ExifTags.TAGS.get(tag, str(tag))
        if tag_name in useful_tags:
            selected_exif[tag_name] = str(value)
    return {
        "exif": {
            "status": "present" if exif_raw or exif else "not_detected",
            "jpeg_exif_segment_count": len(exif_raw),
            "decoded_tag_count": len(exif),
            "selected_decoded_tags": selected_exif,
            "inspection": "JPEG EXIF APP1 header detection and Pillow EXIF decoding.",
        },
        "c2pa": {
            "status": "marker_detected" if c2pa_found else "not_detected_by_limited_scan",
            "jpeg_app11_segment_count": len(app11),
            "c2pa_label_bytes_in_app11": c2pa_found,
            "jumbf_box_marker_bytes_in_app11": jumbf_found,
            "inspection": "Read JPEG APP11 header payloads for literal c2pa and jumb marker bytes.",
            "cryptographic_signature_verification": "not_performed",
            "claim_history_parsed": False,
            "meaning": (
                "C2PA-labelled metadata bytes are present. This does not establish that signatures or claims are valid."
                if c2pa_found else
                "No C2PA label was detected by this limited scan; this does not prove that provenance is absent."
            ),
        },
        "icc_profile_present": bool(image.info.get("icc_profile")),
        "pillow_info_keys": sorted(image.info.keys()),
        "preservation": "The archived original is byte-identical to its PPTX media entry, including all embedded metadata.",
    }


def basic_file_record(path: Path, repo_root: Path, image: Image.Image | None = None) -> dict:
    record = {
        "path": path.relative_to(repo_root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }
    if image is not None:
        record.update({"width": image.width, "height": image.height,
                       "dimensions": [image.width, image.height], "mode": image.mode})
    return record


def save_derivatives(data: bytes, number: int, extension: str, repo_root: Path,
                     reference_quality: int, thumbnail_quality: int,
                     thumbnail_max_edge: int, method: int) -> tuple[dict, dict, dict, dict]:
    stem = f"slide-{number:02d}"
    original_path = repo_root / "assets" / "originals" / (stem + extension)
    reference_path = repo_root / "assets" / "references" / (stem + ".webp")
    thumbnail_path = repo_root / "assets" / "thumbnails" / (stem + ".webp")
    for path in (original_path, reference_path, thumbnail_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    original_path.write_bytes(data)
    if original_path.read_bytes() != data:
        raise RuntimeError(f"Original bytes changed when copying slide {number}")

    with Image.open(io.BytesIO(data)) as source:
        source.load()
        metadata = image_metadata(data, source)
        original = basic_file_record(original_path, repo_root, source)
        original.update({
            "format": source.format,
            "role": "byte_identical_embedded_source",
            "byte_identical_to_pptx_media": True,
            "web_derivative": False,
            "decoded_pixel_sha256": sha256(source.tobytes()),
        })
        work = source.copy()
        if work.mode not in ("RGB", "RGBA"):
            work = work.convert("RGBA" if "transparency" in source.info else "RGB")
        mode_conversion = None if source.mode == work.mode else f"{source.mode} to {work.mode}"
        # Explicitly exclude all EXIF, ICC, XMP, C2PA and other source metadata.
        # The byte-identical original above is the authoritative preserved source.
        work.info.clear()
        work.save(reference_path, "WEBP", quality=reference_quality, method=method,
                  lossless=False, exact=True)
        thumbnail = work.copy()
        thumbnail.thumbnail((thumbnail_max_edge, thumbnail_max_edge), Image.Resampling.LANCZOS)
        thumbnail.info.clear()
        thumbnail.save(thumbnail_path, "WEBP", quality=thumbnail_quality,
                       method=method, lossless=False, exact=True)
        with Image.open(reference_path) as reread:
            reread.load()
            if reread.size != source.size:
                raise RuntimeError(f"Full-size preview changed dimensions on slide {number}")
            reference = basic_file_record(reference_path, repo_root, reread)
            reference["decoded_pixel_sha256"] = sha256(reread.tobytes())
        with Image.open(thumbnail_path) as reread:
            reread.load()
            thumb_record = basic_file_record(thumbnail_path, repo_root, reread)

    for record, role, quality in (
        (reference, "full_resolution_web_reference", reference_quality),
        (thumb_record, "gallery_thumbnail", thumbnail_quality),
    ):
        record.update({
            "format": "WEBP",
            "role": role,
            "web_derivative": True,
            "derived_from_path": original["path"],
            "derived_from_sha256": original["sha256"],
            "pixels_identical_to_source": False,
            "source_metadata_copied": False,
            "c2pa_signature_preserved": False,
            "settings": {
                "encoder": "Pillow WebP",
                "pillow_version": pillow_version,
                "webp_version": features.version("webp"),
                "lossless": False,
                "quality": quality,
                "method": method,
                "exact": True,
                "mode_conversion": mode_conversion,
                "resampling": "none" if role == "full_resolution_web_reference" else "LANCZOS",
                "max_edge": None if role == "full_resolution_web_reference" else thumbnail_max_edge,
                "upscaling": False,
                "retouching": False,
                "exif_orientation_transform": False,
            },
            "note": "A smaller web derivative. Lossy compression changes pixels; use the linked original to inspect the preserved source and its metadata.",
        })
    return original, reference, thumb_record, metadata


def core_metadata(archive: ZipFile) -> dict:
    if "docProps/core.xml" not in archive.namelist():
        return {}
    root = ET.fromstring(archive.read("docProps/core.xml"))
    return {child.tag.rsplit("}", 1)[-1]: child.text for child in root if child.text}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--pptx", type=Path, default=DEFAULT_PPTX)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--reference-quality", type=int, default=90)
    parser.add_argument("--thumbnail-quality", type=int, default=85)
    parser.add_argument("--thumbnail-max-edge", type=int, default=480)
    parser.add_argument("--webp-method", type=int, default=6)
    args = parser.parse_args()
    if not features.check("webp"):
        raise RuntimeError("This Pillow installation has no WebP support")
    for quality in (args.reference_quality, args.thumbnail_quality):
        if not 1 <= quality <= 100:
            parser.error("WebP quality must be in the range 1–100")
    if not 0 <= args.webp_method <= 6 or args.thumbnail_max_edge < 1:
        parser.error("Invalid WebP method or thumbnail maximum edge")

    repo_root = args.root.resolve()
    manifest_raw = args.manifest.read_bytes()
    manifest = json.loads(manifest_raw.decode("utf-8-sig"))
    extracted = {int(item["slide"]): item for item in manifest}
    if len(extracted) != len(manifest):
        raise RuntimeError("Extraction manifest contains duplicate slide numbers")
    parent_sha = file_sha256(args.pptx)
    slides = []
    matched_extractions = set()
    with ZipFile(args.pptx) as archive:
        presentation_path = "ppt/presentation.xml"
        presentation = ET.fromstring(archive.read(presentation_path))
        presentation_rels = relationships(archive, presentation_path)
        ordered_slide_parts = [presentation_rels[node.attrib[REL_ID]]["target"]
                               for node in presentation.findall("p:sldIdLst/p:sldId", NS)]
        container_metadata = core_metadata(archive)
        for number, slide_part in enumerate(ordered_slide_parts, 1):
            slide_xml = ET.fromstring(archive.read(slide_part))
            slide_rels = relationships(archive, slide_part)
            pictures = []
            for picture in slide_xml.findall(".//p:pic", NS):
                blip = picture.find(".//a:blip", NS)
                if blip is None or REL_EMBED not in blip.attrib:
                    continue
                rel_id = blip.attrib[REL_EMBED]
                relationship = slide_rels[rel_id]
                if relationship["external"]:
                    raise RuntimeError(f"External image on slide {number} cannot be archived")
                props = picture.find("p:nvPicPr/p:cNvPr", NS)
                crop = picture.find(".//a:srcRect", NS)
                pictures.append({
                    "relationship_id": rel_id,
                    "internal_path": relationship["target"],
                    "picture_name": props.attrib.get("name") if props is not None else None,
                    "picture_description": props.attrib.get("descr") if props is not None else None,
                    "picture_title": props.attrib.get("title") if props is not None else None,
                    "crop_attributes": dict(crop.attrib) if crop is not None else {},
                })
            record = {
                "slide": number,
                "pptx_slide_path": slide_part,
                "parent_pptx_sha256": parent_sha,
                "has_image": bool(pictures),
                "source_text_objects": [node.text for node in slide_xml.findall(".//a:t", NS) if node.text],
                "pptx_pictures": pictures,
            }
            if not pictures:
                if number in extracted:
                    raise RuntimeError(f"Extraction manifest claims an image on text-only slide {number}")
                record.update({"kind": "text_only_slide", "original": None,
                               "reference": None, "thumbnail": None,
                               "original_path": None, "reference_path": None,
                               "optimized_path": None, "thumbnail_path": None,
                               "original_sha256": None, "derivative_sha256": None})
                slides.append(record)
                continue
            if number not in extracted:
                raise RuntimeError(f"Slide {number} image has no extraction-manifest entry")
            manifest_item = extracted[number]
            extraction_path = Path(manifest_item["path"])
            extraction_data = extraction_path.read_bytes()
            matching = [picture for picture in pictures
                        if archive.read(picture["internal_path"]) == extraction_data]
            if len(matching) != 1:
                raise RuntimeError(f"Expected one byte-identical PPTX image for slide {number}; found {len(matching)}")
            matched = matching[0]
            data = archive.read(matched["internal_path"])
            extension = Path(manifest_item["path"]).suffix.lower()
            original, reference, thumbnail, metadata = save_derivatives(
                data, number, extension, repo_root, args.reference_quality,
                args.thumbnail_quality, args.thumbnail_max_edge, args.webp_method)
            if original["dimensions"] != manifest_item["size"]:
                raise RuntimeError(f"Extraction-manifest dimensions differ on slide {number}")
            record.update({
                "kind": "embedded_image_slide",
                "pptx_media_path": matched["internal_path"],
                "pptx_relationship_id": matched["relationship_id"],
                "source_image_sha256": sha256(data),
                "source_image_bytes": len(data),
                "extraction_manifest_match": {
                    "extracted_filename": extraction_path.name,
                    "sha256": sha256(extraction_data),
                    "byte_identical": True,
                },
                "original": original,
                "reference": reference,
                "thumbnail": thumbnail,
                "original_path": original["path"],
                "reference_path": reference["path"],
                "optimized_path": reference["path"],
                "thumbnail_path": thumbnail["path"],
                "original_sha256": original["sha256"],
                "derivative_sha256": reference["sha256"],
                "source_metadata": metadata,
                "image_generation_model": None,
                "image_generation_model_status": "unknown; not established from supplied context or this metadata inspection",
                "image_generation_history": "not_reconstructed",
            })
            matched_extractions.add(number)
            slides.append(record)
            print(f"Slide {number:02d}: {len(data):,} -> {reference['bytes']:,} bytes; thumb {thumbnail['bytes']:,}")

    if matched_extractions != set(extracted):
        raise RuntimeError("Not every extracted image was matched to a presentation slide")
    image_slides = [slide for slide in slides if slide["has_image"]]
    original_total = sum(slide["original"]["bytes"] for slide in image_slides)
    reference_total = sum(slide["reference"]["bytes"] for slide in image_slides)
    thumbnail_total = sum(slide["thumbnail"]["bytes"] for slide in image_slides)
    c2pa_counts = Counter(slide["source_metadata"]["c2pa"]["status"] for slide in image_slides)
    exif_counts = Counter(slide["source_metadata"]["exif"]["status"] for slide in image_slides)
    provenance = {
        "schema_version": 1,
        "pipeline_version": PIPELINE_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parent_pptx": {
            "filename": args.pptx.name,
            "bytes": args.pptx.stat().st_size,
            "sha256": parent_sha,
            "copied_into_repository": False,
            "core_properties_as_stored": container_metadata,
            "core_properties_interpretation": "Container/account metadata as stored in the PPTX; it does not establish human authorship or image-generation history.",
        },
        "source_context": {
            "collection": "Rough as Guts",
            "material_supplied_in_conversation_as": "Darryl Gough (Daz)'s source material",
            "image_generation_model": None,
            "authorship_or_license_independently_verified": False,
            "note": "Context attribution is separate from metadata. No creator identity, generation dates, prompts, model, ownership chain or missing history has been manufactured.",
        },
        "extraction_manifest": {"filename": args.manifest.name, "sha256": sha256(manifest_raw),
                                "entries": len(manifest), "all_entries_byte_matched": True},
        "policies": {
            "originals": "Byte-identical copies of the embedded PPTX media, including source metadata; no retouching, resizing or recompression.",
            "references": "Full original pixel dimensions. WebP quality 90 by default; lossy encoding changes pixels and omits metadata.",
            "thumbnails": "WebP quality 85 by default, maximum edge 480 pixels, proportional LANCZOS downsampling and no upscaling.",
            "comparison": "Compare each reference.path to its linked original.path; dimensions, byte counts and SHA-256 hashes are recorded for both.",
            "c2pa": "Limited JPEG APP11 marker detection only. No cryptographic signature, claim chain or assertion verification was performed. Original bytes retain the metadata; web derivatives do not carry its signature.",
            "new_artwork_generated": False,
        },
        "summary": {
            "slide_count": len(slides),
            "image_count": len(image_slides),
            "text_only_slides": [slide["slide"] for slide in slides if not slide["has_image"]],
            "original_total_bytes": original_total,
            "reference_total_bytes": reference_total,
            "thumbnail_total_bytes": thumbnail_total,
            "reference_reduction_percent": round((1 - reference_total / original_total) * 100, 2),
            "thumbnail_reduction_percent": round((1 - thumbnail_total / original_total) * 100, 2),
            "all_repository_image_bytes": original_total + reference_total + thumbnail_total,
            "c2pa_marker_status_counts": dict(c2pa_counts),
            "exif_status_counts": dict(exif_counts),
            "all_original_hashes_match_pptx": True,
            "all_reference_dimensions_match_originals": True,
        },
        "slides": slides,
    }
    output_path = repo_root / "data" / "source-provenance.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(provenance["summary"], indent=2))
    print(f"Provenance: {output_path}")


if __name__ == "__main__":
    main()
