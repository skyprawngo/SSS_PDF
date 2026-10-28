"""Convert naturally sorted PNG files without deleting or overwriting inputs."""
from pathlib import Path
import re


def _natural_key(path: Path):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', path.name)]


def create_pdf(input_dir: Path, output_file: Path) -> Path:
    import img2pdf
    source = Path(input_dir).expanduser().resolve()
    destination = Path(output_file).expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f'이미지 폴더가 없습니다: {source}')
    images = sorted((p for p in source.iterdir() if p.is_file() and p.suffix.lower() == '.png'), key=_natural_key)
    if not images:
        raise ValueError('변환할 PNG 이미지가 없습니다.')
    # Convert before opening the destination, so bad inputs leave no partial PDF.
    data = img2pdf.convert([str(p) for p in images])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        try:
            stream.write(data)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
    return destination
