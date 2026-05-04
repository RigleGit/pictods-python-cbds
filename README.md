# pictods-python-cbds
Python script to generate basic .cbds files for ComicBookDS from CBZ/ZIP/images.

PictoDS is very old and can be difficult to run on modern systems, so this script tries to provide a simple command-line alternative for Linux/macOS.

This is not meant to be a perfect replacement for PictoDS, but it should be enough to generate basic `.cbds` files.

## Requirements

Python 3 and Pillow.

Install Pillow with:

```bash
pip install pillow
```

Or using your distro package manager

```bash
sudo apt install python3-pil
sudo dnf install python3-pillow
```

## Usage

Convert a CBZ:

```bash
python3 make_cbds.py comic.cbz
```

Convert a ZIP:

```bash
python3 make_cbds.py comic.zip
```

Manga / right-to-left mode:

```bash
python3 make_cbds.py manga.cbz --rtl -o manga.cbds
```

Lower JPEG quality to reduce file size:

```bash
python3 make_cbds.py comic.cbz -q 80 -o comic.cbds
```

Supported input:
* .cbz
* .zip
* Folder of images

Supported image extensions:
* .jpg
* .jpeg
* .png
* .webp
* .bmp
* .gif

## Notes
The generated .cbds contains the folders expected by ComicBookDS:

* `IMAGE`
* `SMALL_N`
* `THMB_N`
* `SMALL_R`
* `THMB_R`
* `NAME`
* `ComicBookDS_book.ini`

