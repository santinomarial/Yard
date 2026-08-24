#!/bin/bash
set -euo pipefail

project="ios/Yard/Yard.xcodeproj"
scheme="Yard"
destination="platform=iOS Simulator,name=iPhone 17 Pro,OS=latest"

xcodebuild \
  -project "$project" \
  -scheme "$scheme" \
  -destination "$destination" \
  -configuration Debug \
  CODE_SIGNING_ALLOWED=NO \
  clean test
