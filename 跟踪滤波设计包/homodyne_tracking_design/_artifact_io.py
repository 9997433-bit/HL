"""Optional results copy for CI/cloud; never fail the run on missing path."""
import os
from pathlib import Path


def write_results(filename: str, text: str) -> None:
    """Always write locally; optionally mirror to ELLIPSE_ARTIFACTS_DIR."""
    local = Path(__file__).resolve().parent / filename
    local.write_text(text, encoding='utf-8')
    art = os.environ.get('ELLIPSE_ARTIFACTS_DIR')
    if art:
        try:
            Path(art).mkdir(parents=True, exist_ok=True)
            (Path(art) / filename).write_text(text, encoding='utf-8')
        except OSError:
            pass
