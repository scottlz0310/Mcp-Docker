#!/bin/bash
# lefthook pre-commit helper: yamllint が無ければスキップ
command -v yamllint >/dev/null 2>&1 || { echo "warning: yamllint not found, skipping"; exit 0; }
yamllint "$@"
