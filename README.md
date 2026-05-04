# pictods-python-cbds
Python script to generate basic .cbds files for [ComicBookDS](https://www.gamebrew.org/wiki/ComicbookDS) from CBZ/ZIP/CBR/RAR/images.

[PictoDS](https://www.gamebrew.org/wiki/PictoDS) is very old and can be difficult to run on modern systems, so this script tries to provide a simple command-line alternative for Linux/macOS.

This is not meant to be a perfect replacement for PictoDS, but it should be enough to generate basic `.cbds` files.

## Requirements

* Python 3.10+ 
* Pillow
* rarfile

* For .cbr/.rar input: an installed RAR extractor supported by rarfile, such as unrar, unar, or bsdtar

## Installation

### Linux / MacOS

Install Pillow and rarfile with:

```bash
python3 -m pip install -r requirements.txt
```

Or using your distro package manager if using Linux:

```bash
sudo apt install python3-pil
sudo dnf install python3-pillow
```

Also unrar tools (depending on your distro/macOS):

```bash
sudo apt install unrar
sudo dnf install unrar
brew install unrar
```

### Windows

Open PowerShell in the project folder and run

```powershell
py -m pip install -r requirements.txt
```

For Windows, install WinRAR, 7-Zip, or another tool that provides RAR extraction support and make sure it is available in PATH.

## Usage

* On Linux/macOS, use `python3` line
* On Windows, use the `py` line

Convert a CBZ:

```bash
python3 make_cbds.py comic.cbz
py make_cbds.py comic.cbz
```

Convert a ZIP:

```bash
python3 make_cbds.py comic.zip
py make_cbds.py comic.zip
```

Convert a CBR:

```bash
python3 make_cbds.py comic.cbr
py make_cbds.py comic.cbr
```

Convert a folder of images:

```bash
python3 make_cbds.py ./comic_pages -o comic.cbds
py make_cbds.py .\comic_pages -o comic.cbds
```

Manga / right-to-left mode:

```bash
python3 make_cbds.py manga.cbz --rtl -o manga.cbds
py make_cbds.py manga.cbz --rtl -o manga.cbds
```

Lower JPEG quality to reduce file size:

```bash
python3 make_cbds.py comic.cbz -q 80 -o comic.cbds
py make_cbds.py comic.cbz -q 80 -o comic.cbds
```

Supported input:
* .cbz
* .zip
* .cbr
* .rar
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

## Development
Install development dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Run tests:

```bash
python -m pytest -q
```

# License
MIT
