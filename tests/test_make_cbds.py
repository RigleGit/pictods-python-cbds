import io
import sys
import zipfile
import subprocess
from types import SimpleNamespace
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from make_cbds import (
    CBDS_DIRS,
    collect_images_from_dir,
    fit_size,
    make_cbds,
    natural_key,
)


def create_test_image(path: Path, size=(1000, 1500), color=(120, 80, 200)):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, color)
    img.save(path)


def read_text_from_zip(zip_path: Path, member: str) -> str:
    with zipfile.ZipFile(zip_path, "r") as z:
        return z.read(member).decode("utf-8")


def read_image_from_zip(zip_path: Path, member: str) -> Image.Image:
    with zipfile.ZipFile(zip_path, "r") as z:
        data = z.read(member)
    return Image.open(io.BytesIO(data))


def list_zip_entries(zip_path: Path):
    with zipfile.ZipFile(zip_path, "r") as z:
        return set(z.namelist())


def test_fit_size_keeps_aspect_ratio_inside_bounds():
    assert fit_size(1000, 1500, 700, 1054) == (700, 1050)
    assert fit_size(1500, 1000, 256, 169) == (253, 169)


def test_fit_size_handles_invalid_dimensions():
    assert fit_size(0, 100, 700, 1054) == (700, 1054)
    assert fit_size(100, 0, 700, 1054) == (700, 1054)


def test_natural_key_orders_numbered_pages():
    pages = [
        Path("page10.jpg"),
        Path("page2.jpg"),
        Path("page1.jpg"),
    ]

    sorted_pages = sorted(pages, key=natural_key)

    assert [p.name for p in sorted_pages] == [
        "page1.jpg",
        "page2.jpg",
        "page10.jpg",
    ]


def test_collect_images_from_dir_ignores_non_images_and_sorts(tmp_path):
    create_test_image(tmp_path / "page10.jpg")
    create_test_image(tmp_path / "page2.png")
    create_test_image(tmp_path / "page1.jpeg")
    (tmp_path / "notes.txt").write_text("not an image", encoding="utf-8")

    images = collect_images_from_dir(tmp_path)

    assert [p.name for p in images] == [
        "page1.jpeg",
        "page2.png",
        "page10.jpg",
    ]


def test_make_cbds_from_image_folder_creates_expected_structure(tmp_path):
    source = tmp_path / "comic_pages"
    output = tmp_path / "comic.cbds"

    create_test_image(source / "page1.jpg")
    create_test_image(source / "page2.jpg")
    create_test_image(source / "page3.jpg")

    make_cbds(
        source=source,
        output=output,
        title="Test Comic",
        quality=90,
        right_to_left=False,
    )

    assert output.exists()

    entries = list_zip_entries(output)

    expected_files = {
        "ComicBookDS_book.ini",
        "IMAGE/1.jpg",
        "IMAGE/2.jpg",
        "IMAGE/3.jpg",
        "SMALL_N/1.jpg",
        "SMALL_N/2.jpg",
        "SMALL_N/3.jpg",
        "THMB_N/1.jpg",
        "THMB_N/2.jpg",
        "THMB_N/3.jpg",
        "SMALL_R/1.jpg",
        "SMALL_R/2.jpg",
        "SMALL_R/3.jpg",
        "THMB_R/1.jpg",
        "THMB_R/2.jpg",
        "THMB_R/3.jpg",
        "NAME/1.txt",
        "NAME/2.txt",
        "NAME/3.txt",
    }

    assert expected_files.issubset(entries)


def test_make_cbds_writes_ini_metadata(tmp_path):
    source = tmp_path / "comic_pages"
    output = tmp_path / "comic.cbds"

    create_test_image(source / "page1.jpg")
    create_test_image(source / "page2.jpg")

    make_cbds(
        source=source,
        output=output,
        title="My Test Comic",
        quality=85,
        right_to_left=False,
    )

    ini = read_text_from_zip(output, "ComicBookDS_book.ini")

    assert "CbCredits1 = My Test Comic" in ini
    assert "NbPages = 2" in ini
    assert "LeftToRight = 1" in ini
    assert "iQuality = 85" in ini
    assert "oQuality = 85" in ini
    assert "thQuality = 85" in ini


def test_make_cbds_rtl_sets_left_to_right_to_zero(tmp_path):
    source = tmp_path / "manga_pages"
    output = tmp_path / "manga.cbds"

    create_test_image(source / "001.jpg")

    make_cbds(
        source=source,
        output=output,
        title="Manga Test",
        quality=90,
        right_to_left=True,
    )

    ini = read_text_from_zip(output, "ComicBookDS_book.ini")

    assert "LeftToRight = 0" in ini


def test_make_cbds_preserves_original_page_names_in_name_folder(tmp_path):
    source = tmp_path / "comic_pages"
    output = tmp_path / "comic.cbds"

    create_test_image(source / "page10.jpg")
    create_test_image(source / "page2.jpg")
    create_test_image(source / "page1.jpg")

    make_cbds(
        source=source,
        output=output,
        title=None,
        quality=90,
        right_to_left=False,
    )

    assert read_text_from_zip(output, "NAME/1.txt") == "page1.jpg"
    assert read_text_from_zip(output, "NAME/2.txt") == "page2.jpg"
    assert read_text_from_zip(output, "NAME/3.txt") == "page10.jpg"


def test_generated_images_fit_expected_bounds(tmp_path):
    source = tmp_path / "comic_pages"
    output = tmp_path / "comic.cbds"

    create_test_image(source / "page1.jpg", size=(1000, 1500))

    make_cbds(
        source=source,
        output=output,
        title="Bounds Test",
        quality=90,
        right_to_left=False,
    )

    for folder, bounds in CBDS_DIRS.items():
        img = read_image_from_zip(output, f"{folder}/1.jpg")
        max_w, max_h = bounds

        assert img.width <= max_w
        assert img.height <= max_h


def test_make_cbds_from_cbz_input(tmp_path):
    images_dir = tmp_path / "images"
    cbz_path = tmp_path / "comic.cbz"
    output = tmp_path / "comic.cbds"

    create_test_image(images_dir / "001.jpg")
    create_test_image(images_dir / "002.jpg")
    (images_dir / "readme.txt").write_text("ignored", encoding="utf-8")

    with zipfile.ZipFile(cbz_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for file in images_dir.iterdir():
            z.write(file, file.name)

    make_cbds(
        source=cbz_path,
        output=output,
        title="CBZ Test",
        quality=90,
        right_to_left=False,
    )

    assert output.exists()

    ini = read_text_from_zip(output, "ComicBookDS_book.ini")
    assert "NbPages = 2" in ini

    entries = list_zip_entries(output)
    assert "IMAGE/1.jpg" in entries
    assert "IMAGE/2.jpg" in entries


def test_make_cbds_from_zip_input_with_nested_folder(tmp_path):
    images_dir = tmp_path / "images"
    zip_path = tmp_path / "comic.zip"
    output = tmp_path / "comic.cbds"

    create_test_image(images_dir / "chapter1" / "001.jpg")
    create_test_image(images_dir / "chapter1" / "002.jpg")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for file in images_dir.rglob("*"):
            if file.is_file():
                z.write(file, file.relative_to(images_dir))

    make_cbds(
        source=zip_path,
        output=output,
        title="ZIP Test",
        quality=90,
        right_to_left=False,
    )

    ini = read_text_from_zip(output, "ComicBookDS_book.ini")
    assert "NbPages = 2" in ini


def test_make_cbds_from_cbr_input(tmp_path, monkeypatch):
    images_dir = tmp_path / "images"
    cbr_path = tmp_path / "comic.cbr"
    output = tmp_path / "comic.cbds"

    create_test_image(images_dir / "001.jpg")
    create_test_image(images_dir / "002.jpg")
    cbr_path.write_bytes(b"fake rar payload")

    class FakeRarFile:
        def __init__(self, archive_path: Path, mode: str):
            assert archive_path == cbr_path
            assert mode == "r"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extractall(self, dest: Path):
            for file in images_dir.iterdir():
                if file.is_file():
                    (dest / file.name).write_bytes(file.read_bytes())

    monkeypatch.setattr(
        "make_cbds.rarfile",
        SimpleNamespace(RarFile=FakeRarFile, RarCannotExec=RuntimeError),
    )

    make_cbds(
        source=cbr_path,
        output=output,
        title="CBR Test",
        quality=90,
        right_to_left=False,
    )

    assert output.exists()
    ini = read_text_from_zip(output, "ComicBookDS_book.ini")
    assert "NbPages = 2" in ini


def test_make_cbds_rejects_missing_source(tmp_path):
    missing = tmp_path / "missing.cbz"
    output = tmp_path / "out.cbds"

    with pytest.raises(FileNotFoundError):
        make_cbds(
            source=missing,
            output=output,
            title=None,
            quality=90,
            right_to_left=False,
        )


def test_make_cbds_reports_missing_rar_extractor(tmp_path, monkeypatch):
    source = tmp_path / "comic.rar"
    output = tmp_path / "out.cbds"

    source.write_bytes(b"not actually a rar")

    class FakeRarCannotExec(Exception):
        pass

    class FakeRarFile:
        def __init__(self, archive_path: Path, mode: str):
            assert archive_path == source
            assert mode == "r"

        def __enter__(self):
            raise FakeRarCannotExec("missing extractor")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "make_cbds.rarfile",
        SimpleNamespace(RarFile=FakeRarFile, RarCannotExec=FakeRarCannotExec),
    )

    with pytest.raises(RuntimeError, match="RAR extraction requires"):
        make_cbds(
            source=source,
            output=output,
            title=None,
            quality=90,
            right_to_left=False,
        )

def test_make_cbds_rejects_unsupported_file_type(tmp_path):
    source = tmp_path / "comic.7z"
    output = tmp_path / "out.cbds"

    source.write_bytes(b"not actually a 7z")

    with pytest.raises(ValueError, match="supports image folders"):
        make_cbds(
            source=source,
            output=output,
            title=None,
            quality=90,
            right_to_left=False,
        )


def test_make_cbds_rejects_empty_folder(tmp_path):
    source = tmp_path / "empty"
    output = tmp_path / "out.cbds"

    source.mkdir()

    with pytest.raises(RuntimeError, match="No images found"):
        make_cbds(
            source=source,
            output=output,
            title=None,
            quality=90,
            right_to_left=False,
        )


def test_make_cbds_rejects_invalid_quality_low(tmp_path):
    source = tmp_path / "comic_pages"
    output = tmp_path / "out.cbds"

    create_test_image(source / "001.jpg")

    with pytest.raises(ValueError, match="JPEG quality"):
        make_cbds(
            source=source,
            output=output,
            title=None,
            quality=0,
            right_to_left=False,
        )


def test_make_cbds_rejects_invalid_quality_high(tmp_path):
    source = tmp_path / "comic_pages"
    output = tmp_path / "out.cbds"

    create_test_image(source / "001.jpg")

    with pytest.raises(ValueError, match="JPEG quality"):
        make_cbds(
            source=source,
            output=output,
            title=None,
            quality=101,
            right_to_left=False,
        )


def test_cli_creates_cbds_file(tmp_path):
    source = tmp_path / "comic_pages"
    output = tmp_path / "cli_output.cbds"

    create_test_image(source / "001.jpg")
    create_test_image(source / "002.jpg")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "make_cbds.py"),
            str(source),
            "-o",
            str(output),
            "-t",
            "CLI Test",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output.exists()
    assert "[OK] Created:" in result.stdout

    ini = read_text_from_zip(output, "ComicBookDS_book.ini")
    assert "CbCredits1 = CLI Test" in ini
    assert "NbPages = 2" in ini
