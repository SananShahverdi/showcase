#!/usr/bin/env python3
"""Generate responsive AVIF and WebP derivatives for referenced portfolio images.

The source list is derived from ``src/data/projects.ts`` so this script only
processes images that the current site actually uses. Outputs are written below
``portfolio_assets/optimized`` and are safe to regenerate.
"""

from __future__ import annotations

import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from PIL import Image, ImageOps, features


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_DATA = WORKSPACE_ROOT / "src" / "data" / "projects.ts"
ASSET_ROOT = WORKSPACE_ROOT / "portfolio_assets"
OUTPUT_ROOT = ASSET_ROOT / "optimized"

BREAKPOINT_WIDTHS = (480, 768, 1280)
AVIF_QUALITY = 50
WEBP_QUALITY = 80
MAX_WORKERS = min(4, max(1, os.cpu_count() or 1))

SOURCE_PATTERN = re.compile(
    r"""\bsrc\s*:\s*["'](?P<url>/[^"']+\.jpg)["']""",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class SourceImage:
    path: Path
    relative_path: Path
    width: int
    height: int
    target_widths: tuple[int, ...]


@dataclass(frozen=True)
class Derivative:
    path: Path
    source_path: Path
    width: int
    height: int
    image_format: str
    byte_size: int
    is_native_width: bool


def referenced_source_paths() -> list[tuple[Path, Path]]:
    """Return unique, validated source paths in their first-seen order."""
    source_text = PROJECT_DATA.read_text(encoding="utf-8")
    asset_root = ASSET_ROOT.resolve()
    references: list[tuple[Path, Path]] = []
    seen: set[Path] = set()

    for match in SOURCE_PATTERN.finditer(source_text):
        url_path = PurePosixPath(match.group("url").lstrip("/"))
        if url_path.is_absolute() or ".." in url_path.parts:
            raise ValueError(f"Unsafe portfolio asset URL: {match.group('url')}")

        relative_path = Path(*url_path.parts)
        source_path = (ASSET_ROOT / relative_path).resolve()
        if not source_path.is_relative_to(asset_root):
            raise ValueError(f"Asset escapes portfolio_assets: {match.group('url')}")
        if source_path in seen:
            continue
        if not source_path.is_file():
            raise FileNotFoundError(f"Referenced portfolio asset is missing: {source_path}")

        seen.add(source_path)
        references.append((source_path, relative_path))

    if not references:
        raise RuntimeError(f"No referenced JPEGs found in {PROJECT_DATA}")

    return references


def inspect_source(source_path: Path, relative_path: Path) -> SourceImage:
    """Read oriented dimensions and calculate all non-upscaled target widths."""
    with Image.open(source_path) as image:
        oriented = ImageOps.exif_transpose(image)
        width, height = oriented.size

    if width < 1 or height < 1:
        raise ValueError(f"Invalid image dimensions for {source_path}: {width}x{height}")

    # Always retain a modern-format image at native width. This is important for
    # originals whose width does not land exactly on a standard breakpoint.
    target_widths = tuple(
        sorted({candidate for candidate in BREAKPOINT_WIDTHS if candidate <= width} | {width})
    )
    return SourceImage(
        path=source_path,
        relative_path=relative_path,
        width=width,
        height=height,
        target_widths=target_widths,
    )


def metadata_free_rgb(image: Image.Image) -> Image.Image:
    """Flatten an image into a fresh RGB allocation with no carried metadata."""
    if image.has_transparency_data:
        rgba = image.convert("RGBA")
        clean = Image.new("RGB", rgba.size, "white")
        clean.paste(rgba, mask=rgba.getchannel("A"))
    else:
        clean = Image.new("RGB", image.size)
        clean.paste(image.convert("RGB"))
    clean.info.clear()
    return clean


def derivative_path(source: SourceImage, width: int, extension: str) -> Path:
    parent = OUTPUT_ROOT / source.relative_path.parent
    return parent / f"{source.relative_path.stem}-w{width}.{extension}"


def atomic_save(image: Image.Image, destination: Path, image_format: str) -> None:
    """Encode to a temporary sibling, then atomically replace the destination."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.stem}-",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)

    try:
        if image_format == "AVIF":
            image.save(
                temporary_path,
                format="AVIF",
                quality=AVIF_QUALITY,
                speed=6,
                subsampling="4:2:0",
                max_threads=1,
            )
        elif image_format == "WEBP":
            image.save(
                temporary_path,
                format="WEBP",
                quality=WEBP_QUALITY,
                method=6,
                exact=True,
            )
        else:
            raise ValueError(f"Unsupported output format: {image_format}")
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def validate_derivative(
    path: Path,
    expected_size: tuple[int, int],
    expected_format: str,
) -> None:
    with Image.open(path) as image:
        image.load()
        if image.size != expected_size:
            raise RuntimeError(
                f"Unexpected dimensions for {path}: {image.size}, expected {expected_size}"
            )
        if image.format != expected_format:
            raise RuntimeError(
                f"Unexpected format for {path}: {image.format}, expected {expected_format}"
            )
        if image.getexif() or image.info.get("icc_profile") or image.info.get("xmp"):
            raise RuntimeError(f"Unexpected metadata retained in {path}")


def generate_source(source: SourceImage) -> list[Derivative]:
    derivatives: list[Derivative] = []

    with Image.open(source.path) as opened:
        opened.load()
        oriented = ImageOps.exif_transpose(opened)
        native = metadata_free_rgb(oriented)

    for width in source.target_widths:
        height = max(1, round(source.height * width / source.width))
        if width == source.width:
            resized = native
        else:
            resized = native.resize((width, height), resample=Image.Resampling.LANCZOS)
            resized.info.clear()

        for image_format, extension in (("AVIF", "avif"), ("WEBP", "webp")):
            output_path = derivative_path(source, width, extension)
            atomic_save(resized, output_path, image_format)
            validate_derivative(output_path, (width, height), image_format)
            derivatives.append(
                Derivative(
                    path=output_path,
                    source_path=source.path,
                    width=width,
                    height=height,
                    image_format=image_format,
                    byte_size=output_path.stat().st_size,
                    is_native_width=width == source.width,
                )
            )

        if resized is not native:
            resized.close()

    native.close()
    return derivatives


def format_bytes(byte_count: int) -> str:
    value = float(byte_count)
    units = ("B", "KiB", "MiB", "GiB")
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")


def savings_text(original_bytes: int, derivative_bytes: int) -> str:
    difference = original_bytes - derivative_bytes
    percentage = (difference / original_bytes * 100) if original_bytes else 0.0
    direction = "saved" if difference >= 0 else "larger"
    return f"{format_bytes(abs(difference))} {direction} ({abs(percentage):.1f}%)"


def main() -> None:
    if not features.check("avif"):
        raise RuntimeError("This Pillow build does not support AVIF encoding")
    if not features.check("webp"):
        raise RuntimeError("This Pillow build does not support WebP encoding")

    sources = [
        inspect_source(source_path, relative_path)
        for source_path, relative_path in referenced_source_paths()
    ]
    original_bytes = sum(source.path.stat().st_size for source in sources)
    derivatives: list[Derivative] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_source = {
            executor.submit(generate_source, source): source for source in sources
        }
        for completed_count, future in enumerate(as_completed(future_to_source), start=1):
            source = future_to_source[future]
            derivatives.extend(future.result())
            print(
                f"[{completed_count:02d}/{len(sources):02d}] "
                f"{source.relative_path.as_posix()} "
                f"({source.width}x{source.height})"
            )

    derivatives.sort(key=lambda item: item.path.as_posix())
    avif_native_bytes = sum(
        item.byte_size
        for item in derivatives
        if item.image_format == "AVIF" and item.is_native_width
    )
    webp_native_bytes = sum(
        item.byte_size
        for item in derivatives
        if item.image_format == "WEBP" and item.is_native_width
    )
    all_derivative_bytes = sum(item.byte_size for item in derivatives)

    print()
    print(f"Referenced sources: {len(sources)}")
    print(f"Generated files:    {len(derivatives)}")
    print(f"Original JPEGs:     {format_bytes(original_bytes)}")
    print(
        f"Native AVIF set:    {format_bytes(avif_native_bytes)} "
        f"— {savings_text(original_bytes, avif_native_bytes)}"
    )
    print(
        f"Native WebP set:    {format_bytes(webp_native_bytes)} "
        f"— {savings_text(original_bytes, webp_native_bytes)}"
    )
    print(f"All derivatives:    {format_bytes(all_derivative_bytes)}")
    print(f"Output directory:   {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
