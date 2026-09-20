#!/usr/bin/env bash
#
# Build an APK, keep it in release/ under its version, and put a copy on the
# connected phone.
#
# Two names for one file, deliberately. release/pana-<version>.apk is the
# archive, so an older build can be reinstalled when a new one misbehaves.
# Downloads/pana.apk on the handset is the stable name, so installing from the
# phone's file manager means tapping the same entry every time rather than
# hunting for the newest.
#
# Usage: npm run release        # release build, signed with the release key
#        npm run release debug  # debug build, for a quick iteration
set -euo pipefail

cd "$(dirname "$0")/.."

ANDROID_HOME="${ANDROID_HOME:-$HOME/Android/Sdk}"
export ANDROID_HOME
export PATH="$PATH:$ANDROID_HOME/platform-tools"

# Release is the default. A debug build is half a minute faster because it
# skips R8, which is worth having while iterating, but it is signed with the
# shared Android debug key -- which is what makes Play Protect call an app
# unsafe, so it is never what goes to anybody else.
VARIANT="${1:-release}"

case "$VARIANT" in
  release)
    GRADLE_TASK="assembleRelease"
    BUILT="android/app/build/outputs/apk/release/app-release.apk"
    ;;
  debug)
    GRADLE_TASK="assembleDebug"
    BUILT="android/app/build/outputs/apk/debug/app-debug.apk"
    ;;
  *)
    echo "Unknown variant '$VARIANT'. Use 'release' or 'debug'." >&2
    exit 1
    ;;
esac

if [ "$VARIANT" = "release" ] && [ ! -f ../secrets/android_signing.env ]; then
  echo "==> secrets/android_signing.env is missing." >&2
  echo "    Without it the release build falls back to the debug signature," >&2
  echo "    which is what Play Protect warns about. See pana-mobile/CONFIG.md." >&2
  exit 1
fi

VERSION="$(node -p "require('./package.json').version")"
STAMP="$(date +%Y%m%d-%H%M)"
OUT="release/pana-${VERSION}-${STAMP}.apk"

echo "==> Building web bundle"
npm run build

echo "==> Syncing to Android"
npx cap sync android

echo "==> Assembling ${VARIANT} APK"
(cd android && ./gradlew "$GRADLE_TASK")

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
  # A debug and a release APK are signed by different keys, and Android will
  # not replace one with the other. Reinstalling over a mismatched signature
  # fails, so the old app is removed first -- which does sign the user out.
  if ! adb install -r "$BUILT" 2>&1 | tail -2 | grep -q Success; then
    echo "==> Signature differs from the installed build; reinstalling"
    adb uninstall com.pana.app >/dev/null 2>&1 || true
    adb install "$BUILT" 2>&1 | tail -2
  fi
  echo "==> Done. Pana is on the phone."
else
  echo "==> No device connected; APK is in release/ only."
fi
