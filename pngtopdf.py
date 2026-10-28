"""Convert PNG images: python pngtopdf.py INPUT_DIRECTORY OUTPUT.pdf."""
import sys
from sss_pdf.cli import main

if __name__ == '__main__':
    raise SystemExit(main(['pdf', *sys.argv[1:]]))
