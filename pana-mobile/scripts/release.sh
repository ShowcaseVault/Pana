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
#        npm run release debug  # debug build, which can be pointed at any server
#        npm run release both   # both, for publishing
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
  release|debug|both) ;;
  *)
    echo "Unknown variant '$VARIANT'. Use 'release', 'debug' or 'both'." >&2
    exit 1
    ;;
esac

if [ "$VARIANT" != "debug" ] && [ ! -f ../secrets/android_signing.env ]; then
  echo "==> secrets/android_signing.env is missing." >&2
  echo "    Without it the release build falls back to the debug signature," >&2
  echo "    which is what Play Protect warns about. See pana-mobile/CONFIG.md." >&2
  exit 1
fi

VERSION="$(node -p "require('./package.json').version")"
STAMP="$(date +%Y%m%d-%H%M)"

mkdir -p release

# Only the current build is kept. The archive was meant to make an older APK
# reinstallable, but every build overwrote the phone's copy anyway, and a
# directory of near-identical files is not a version history: git is. A
# specific older build comes from checking out its commit and rebuilding.
rm -f release/*.apk

# Build one variant, and leave its APK in release/ under a name that says
# which variant it is.
#
# The web bundle is rebuilt per variant, not once: whether the server address
# can be changed at runtime is compiled into it. VITE_ALLOW_SERVER_OVERRIDE is
# what the debug bundle carries and the release bundle does not, so the
# release bundle has no code path that points the app at another server.
build_variant() {
  local variant="$1"
  local task out built

  case "$variant" in
    release)
      task="assembleRelease"
      built="android/app/build/outputs/apk/release/app-release.apk"
      out="release/pana-${VERSION}-${STAMP}.apk"
      ;;
    debug)
      task="assembleDebug"
      built="android/app/build/outputs/apk/debug/app-debug.apk"
      out="release/pana-${VERSION}-${STAMP}-debug.apk"
      ;;
  esac

  echo "==> Building web bundle (${variant})"
  if [ "$variant" = "debug" ]; then
    VITE_ALLOW_SERVER_OVERRIDE=true npm run build
  else
    npm run build
  fi

  echo "==> Syncing to Android"
  npx cap sync android

  echo "==> Assembling ${variant} APK"
  (cd android && ./gradlew "$task")

  cp "$built" "$out"
  echo "==> Built $out ($(du -h "$out" | cut -f1))"

  # The path of the APK to install, for the caller.
  LAST_BUILT="$built"
}

if [ "$VARIANT" = "both" ]; then
  # Release first, so the debug build is the one left installed: it is the one
  # that can be pointed at a LAN server, which is what a person testing wants.
  build_variant release
  build_variant debug
else
  build_variant "$VARIANT"
fi

# The unversioned copy is what a person actually taps on the phone.
cp "$LAST_BUILT" "release/pana.apk"

# Pushing and installing are separate on purpose: the push leaves a file the
# user can reinstall from the phone itself later, and the install is what makes
# this build the one running now.
if adb get-state >/dev/null 2>&1; then
  DEVICE="$(adb devices | awk 'NR==2 {print $1}')"
  echo "==> Copying to $DEVICE:/sdcard/Download/pana.apk"
  adb push "$LAST_BUILT" /sdcard/Download/pana.apk >/dev/null

  echo "==> Installing"
  # A debug and a release APK are signed by different keys, and Android will
  # not replace one with the other, so a mismatch means removing the old app
  # first. That does sign the user out.
  if ! adb install -r "$LAST_BUILT" 2>&1 | tail -2 | grep -q Success; then
    echo "==> Signature differs from the installed build; reinstalling"
    adb uninstall com.pana.app >/dev/null 2>&1 || true
    adb install "$LAST_BUILT" 2>&1 | tail -2
  fi
  echo "==> Done. Pana is on the phone."
else
  echo "==> No device connected; APKs are in release/ only."
fi
