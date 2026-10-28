"""Command-line entry points shared with the local web application."""
import argparse
from pathlib import Path
import sys
from .config import AppConfig


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='SSS PDF — 브라우저 캡처 및 PNG → PDF')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('login', 'capture'):
        command = commands.add_parser(name)
        command.add_argument('--url', default='', required=name == 'capture')
        command.add_argument('--pages', type=int, default=5)
        command.add_argument('--output-dir', type=Path, default=Path('SS_temp'))
        command.add_argument('--profile-dir', type=Path)
        command.add_argument('--chrome-path')
        command.add_argument('--headless', action='store_true')
        command.add_argument('--timeout', type=float, default=20)
        if name == 'capture':
            command.add_argument('--cookies-file', type=Path, help='대상 호스트에 적용할 쿠키 JSON 파일 (선택)')
    pdf = commands.add_parser('pdf')
    pdf.add_argument('input_dir', type=Path)
    pdf.add_argument('output_file', type=Path)
    serve = commands.add_parser('serve')
    serve.add_argument('--port', type=int, default=8765)
    serve.add_argument('--no-browser', action='store_true', help='자동 브라우저 열기 끄기 (CI용)')
    arguments = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(arguments or ['serve'])
    try:
        if args.command == 'serve':
            from .web import main as serve_main
            serve_main(host='127.0.0.1', port=args.port, open_browser=not args.no_browser)
        elif args.command == 'pdf':
            from .pdf import create_pdf
            print(create_pdf(args.input_dir, args.output_file))
        else:
            from .browser import capture, login
            settings = vars(args).copy()
            settings.pop('command')
            config = AppConfig(**settings)
            if args.command == 'login':
                print('로그인한 뒤 열린 브라우저 창을 닫으세요. 세션이 저장됩니다.')
                login(config)
            else:
                files = capture(config, progress=print)
                print(f'{len(files)}개 이미지 저장: {files[0].parent}')
    except (Exception, KeyboardInterrupt) as exc:
        print(f'오류: {exc or "작업 취소"}', file=sys.stderr)
        return 1
    return 0
