#!/usr/bin/env python3
import argparse
import os
import tempfile
import zipfile
from pathlib import Path

import rarfile
from PIL import Image, ImageOps

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
ZIP_ARCHIVE_EXTS = {".cbz", ".zip"}
RAR_ARCHIVE_EXTS = {".cbr", ".rar"}

# Folders expected by ComicBookDS
CBDS_DIRS = {
    "IMAGE":   (700, 1054),  # main normal image
    "SMALL_N": (127, 192),   # normal preview
    "THMB_N":  (30, 46),     # normal thumbnail
    "SMALL_R": (256, 169),   # rotated preview
    "THMB_R":  (62, 40),     # rotated thumbnail
}


def natural_key(path: Path):
    """
    Simple natural sorting:
    page2.jpg comes before page10.jpg.
    """
    import re
    parts = re.split(r"(\d+)", path.name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def fit_size(w: int, h: int, max_w: int, max_h: int):
    """
    Keep aspect ratio inside max_w x max_h.
    """
    if w <= 0 or h <= 0:
        return max_w, max_h

    scale = min(max_w / w, max_h / h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return new_w, new_h


def collect_images_from_dir(directory: Path):
    images = []

    for root, _, files in os.walk(directory):
        for name in files:
            p = Path(root) / name
            if p.suffix.lower() in IMAGE_EXTS:
                images.append(p)

    return sorted(images, key=natural_key)


def extract_zip(zip_path: Path, dest: Path):
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest)


def extract_rar(rar_path: Path, dest: Path):
    try:
        with rarfile.RarFile(rar_path, "r") as archive:
            archive.extractall(dest)
    except rarfile.RarCannotExec as exc:
        raise RuntimeError(
            "RAR extraction requires an installed unrar-compatible tool. "
            "Install unrar, unar, 7zip, or bsdtar and try again."
        ) from exc
    except rarfile.Error as exc:
        raise RuntimeError(
            f"Could not extract RAR/CBR archive: {rar_path}"
        ) from exc


def save_jpeg(img: Image.Image, out_path: Path, quality: int):
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    img.save(out_path, "JPEG", quality=quality, optimize=True)


def generate_page_variants(src: Path, page_num: int, workdir: Path, quality: int):
    with Image.open(src) as raw:
        img = ImageOps.exif_transpose(raw).convert("RGB")

        for folder, bounds in CBDS_DIRS.items():
            variant = img

            # *_R folders are rotated versions for landscape mode.
            if folder.endswith("_R"):
                variant = variant.rotate(-90, expand=True)

            new_w, new_h = fit_size(
                variant.width,
                variant.height,
                bounds[0],
                bounds[1],
            )

            variant = variant.resize((new_w, new_h), Image.Resampling.LANCZOS)
            save_jpeg(variant, workdir / folder / f"{page_num}.jpg", quality)

    # Original page name
    name_file = workdir / "NAME" / f"{page_num}.txt"
    name_file.write_text(str(src.name), encoding="utf-8")


def write_ini(
    workdir: Path,
    title: str,
    pages: int,
    quality: int,
    right_to_left: bool,
):
    left_to_right = 0 if right_to_left else 1

    ini = f"""; ComicBookDS ini file

; 1st line displayed in the credits
CbCredits1 = {title}

; 2nd line displayed in the credits
CbCredits2 = Unknown

; 3rd line displayed in the credits
CbCredits3 = Unknown

; Left To Right reading mode [RightToLeft=0,LeftToRight=1]
LeftToRight = {left_to_right}

; The number of pages contained in this comic book
NbPages = {pages}

; Compatibility version
Version = 200

iHeight = 1400
iQuality = {quality}
iSize = 860000
iWidth = 700

oHeight = 192
oQuality = {quality}
oSize = 0
oWidth = 256

thHeight = 46
thQuality = {quality}
thSize = 0
thWidth = 62
"""

    (workdir / "ComicBookDS_book.ini").write_text(ini, encoding="utf-8")


def make_cbds(
    source: Path,
    output: Path,
    title: str | None,
    quality: int,
    right_to_left: bool,
):
    source = source.resolve()
    output = output.resolve()

    if not source.exists():
        raise FileNotFoundError(f"File does not exist: {source}")

    if not 1 <= quality <= 100:
        raise ValueError("JPEG quality must be between 1 and 100.")

    with tempfile.TemporaryDirectory(prefix="make_cbds_") as tmp:
        tmp = Path(tmp)
        input_dir = tmp / "input"
        workdir = tmp / "cbds_work"

        input_dir.mkdir()
        workdir.mkdir()

        for folder in list(CBDS_DIRS.keys()) + ["NAME"]:
            (workdir / folder).mkdir(parents=True, exist_ok=True)

        if source.is_dir():
            images_dir = source
        elif source.suffix.lower() in ZIP_ARCHIVE_EXTS:
            extract_zip(source, input_dir)
            images_dir = input_dir
        elif source.suffix.lower() in RAR_ARCHIVE_EXTS:
            extract_rar(source, input_dir)
            images_dir = input_dir
        else:
            raise ValueError(
                "This script supports image folders, .cbz, .zip, .cbr and .rar files."
            )

        images = collect_images_from_dir(images_dir)

        if not images:
            raise RuntimeError("No images found in the input.")

        book_title = title or source.stem

        print(f"[INFO] Book: {book_title}")
        print(f"[INFO] Pages found: {len(images)}")

        for idx, img_path in enumerate(images, start=1):
            print(f"[{idx}/{len(images)}] {img_path.name}")
            generate_page_variants(img_path, idx, workdir, quality)

        write_ini(
            workdir=workdir,
            title=book_title,
            pages=len(images),
            quality=quality,
            right_to_left=right_to_left,
        )

        output.parent.mkdir(parents=True, exist_ok=True)

        if output.exists():
            output.unlink()

        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(workdir):
                for name in files:
                    full = Path(root) / name
                    rel = full.relative_to(workdir)
                    z.write(full, rel.as_posix())

        print(f"[OK] Created: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert an image folder or CBZ/ZIP/CBR/RAR file to CBDS for ComicBookDS."
    )

    parser.add_argument("source", help="Input folder, .cbz, .zip, .cbr or .rar")

    parser.add_argument(
        "-o",
        "--output",
        help="Output .cbds file. By default it uses the input filename.",
    )

    parser.add_argument(
        "-t",
        "--title",
        help="Title written into the CBDS ini file.",
    )

    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=90,
        help="JPEG quality, 1-100. Default: 90.",
    )

    parser.add_argument(
        "--rtl",
        action="store_true",
        help="Manga / right-to-left reading mode.",
    )

    args = parser.parse_args()

    source = Path(args.source)

    if args.output:
        output = Path(args.output)
    else:
        output = source.with_suffix(".cbds")

    make_cbds(
        source=source,
        output=output,
        title=args.title,
        quality=args.quality,
        right_to_left=args.rtl,
    )


if __name__ == "__main__":
    main()
