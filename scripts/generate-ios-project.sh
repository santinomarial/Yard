#!/usr/bin/env bash
set -euo pipefail

if ! command -v xcodegen >/dev/null 2>&1; then
  echo "XcodeGen 2.46 or later is required: https://github.com/yonaskolb/XcodeGen"
  exit 1
fi

xcodegen generate --spec ios/Yard/project.yml

