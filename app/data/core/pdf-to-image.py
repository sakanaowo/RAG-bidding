"""Utilities for converting PDF documents to image sequences."""

from pathlib import Path
from typing import Iterable, List

from pdf2image import convert_from_path
from tqdm import tqdm


def pdf_to_images(
    pdf_path: str | Path,
    *,
    output_root: str | Path = "app/data/processed/_image-process",
    dpi: int = 400,
) -> List[Path]:
    """Render each page in ``pdf_path`` to PNG files under ``output_root``.

    The output directory is ``app/data/processed/<pdf-name>-images`` by default. Returns the
    list of image paths, ordered by page number. Raises ``FileNotFoundError`` if the
    PDF does not exist.
    """

    source = Path(pdf_path)
    if not source.is_file():
        raise FileNotFoundError(f"PDF not found: {source}")

    destination = Path(output_root) / f"{source.stem}-images"
    destination.mkdir(parents=True, exist_ok=True)

    # 300-400 DPI yields good OCR quality without huge files.
    print(f"Converting PDF to images at {dpi} DPI...")
    pages: Iterable = convert_from_path(str(source), dpi=dpi)

    # Convert to list to get length for progress bar
    pages_list = list(pages)
    print(f"Found {len(pages_list)} pages to process")

    saved_paths: List[Path] = []
    for index, image in enumerate(tqdm(pages_list, desc="Saving images"), start=1):
        image_path = destination / f"page_{index:03}.png"
        image.save(image_path, "PNG")
        saved_paths.append(image_path)

    return saved_paths


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert a PDF into page images")
    parser.add_argument("pdf_path", help="Path to the source PDF file")
    parser.add_argument(
        "--output-root",
        default="app/data/processed/_image-process",
        help="Directory where per-PDF image folders will be created",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=400,
        help="Rendering resolution in dots per inch (default: 400)",
    )

    args = parser.parse_args()

    try:
        images = pdf_to_images(
            args.pdf_path, output_root=args.output_root, dpi=args.dpi
        )
    except FileNotFoundError as exc:
        parser.error(str(exc))

    if not images:
        print("No pages were rendered")
    else:
        print(f"Saved {len(images)} images to: {images[0].parent}")
