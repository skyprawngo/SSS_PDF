"""Keep Korean CLI messages readable in redirected Windows output."""
import sys


def configure_console():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
