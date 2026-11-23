"""Entry for make.fun news-image-20261123.

Writes the 23 November 2026 world-news front page to the output
directory. The image is drawn in advance and shipped beside this
program; the grader runs with no network, so this program only
copies the bundled file, deterministically, every run.
"""

import os
import shutil
from pathlib import Path


def main() -> None:
    here = Path(__file__).resolve().parent
    source = here / "entry.png"
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "entry.png"
    shutil.copyfile(source, target)
    # Guard the gate limits: at most 1024x1024 px and 1 MiB. The PNG
    # header carries the dimensions, so check them without any
    # third-party library (stdlib only, no network).
    data = target.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "entry.png is not a PNG"
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    assert width <= 1024 and height <= 1024, "image too large"
    assert len(data) <= 1_048_576, "image over 1 MiB"


if __name__ == "__main__":
    main()
