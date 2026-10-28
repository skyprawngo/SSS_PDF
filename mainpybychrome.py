"""Compatibility entry point. Use `python mainpybychrome.py login/capture ...`."""
from sss_pdf.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
