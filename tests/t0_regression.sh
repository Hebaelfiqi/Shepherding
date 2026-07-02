#!/bin/bash
# T0 baseline regression (REQUIREMENTS.md Section 6.1): with AdversarialMode off, a
# fixed-seed run of the shipped Config.xml must reproduce the recorded trajectory hash.
# Usage: t0_regression.sh <build-dir-with-shepherd_sim> <repo-root>
set -e
BUILD="$1"
SRC="$2"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
cp "$SRC/InputFiles/Config.xml" "$TMP/"
cd "$TMP"
"$BUILD/shepherd_sim" Config.xml > /dev/null
NEW=$(sha256sum Config_OutPutData.csv | cut -d' ' -f1)
REF=$(cut -d' ' -f1 "$SRC/tests/baseline/T0_sha256.txt")
if [ "$NEW" = "$REF" ]; then
    echo "T0 PASS: trajectory hash matches baseline"
else
    echo "T0 FAIL: $NEW != $REF"
    exit 1
fi
