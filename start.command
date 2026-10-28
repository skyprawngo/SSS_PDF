#!/bin/bash
cd -- "$(dirname -- "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  python3 run.py "$@"
else
  echo "Python 3.11 이상을 설치한 뒤 다시 실행하세요."
  exit 1
fi
