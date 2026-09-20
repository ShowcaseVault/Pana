#!/usr/bin/env bash
#
# Build a debug APK, keep it in release/ under its version, and put a copy on
# the connected phone.
#
# Two names for one file, deliberately. release/pana-<version>.apk is the
# archive, so an older build can be reinstalled when a new one misbehaves.
# Downloads/pana.apk on the handset is the stable name, so installing from the
# phone's file manager means tapping the same entry every time rather than
# hunting for the newest.
#
# Usage: npm run release
set -euo pipefail

cd "$(dirname "$0")/.."

ANDROID_HOME="${ANDROID_HOME:-$HOME/Android/Sdk}"
export ANDROID_HOME
export PATH="$PATH:$ANDROID_HOME/platform-tools"

VERSION="$(node -p "require('./package.json').version")"
STAMP="$(date +%Y%m%d-%H%M)"
OUT="release/pana-${VERSION}-${STAMP}.apk"
BUILT="android/app/build/outputs/apk/debug/app-debug.apk"

echo "==> Building web bundle"
npm run build

echo "==> Syncing to Android"
npx cap sync android

echo "==> Assembling debug APK"
(cd android && ./gradlew assembleDebug)

mkdir -p release
cp "$BUILT" "$OUT"

# The unversioned copy is what a person actually taps; the versioned one is the
# archive beside it.
cp "$BUILT" "release/pana.apk"

SIZE="$(du -h "$OUT" | cut -f1)"
echo "==> Built $OUT ($SIZE)"

# Pushing and installing are separate on purpose: the push leaves a file the
# user can reinstall from the phone itself later, and the install is what makes
# this build the one running now.
if adb get-state >/dev/null 2>&1; then
  DEVICE="$(adb devices | awk 'NR==2 {print $1}')"
  echo "==> Copying to $DEVICE:/sdcard/Download/pana.apk"
  adb push "$BUILT" /sdcard/Download/pana.apk >/dev/null

  echo "==> Installing"
  # -r replaces the existing app while keeping its data, so a rebuild does not
  # sign the user out on every iteration.
  adb install -r "$BUILT" 2>&1 | tail -2
  echo "==> Done. Pana is on the phone."
else
  echo "==> No device connected; APK is in release/ only."
fi
