#!/bin/sh
set -eu
# Kept beside the stable project so Xcode Cloud discovers this hook.
python3 -I "$(dirname "$0")/../prepare-cloud.py"
