#!/bin/bash
# lefthook pre-commit helper: shellcheck が無ければスキップ
command -v shellcheck >/dev/null 2>&1 || { echo "warning: shellcheck not found, skipping"; exit 0; }
shellcheck "$@"
