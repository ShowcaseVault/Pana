#!/usr/bin/env bash
#
# Publish the built APK as a GitHub release.
#
# The APK is a build artefact, so it is not in the repository -- release/ is
# git-ignored, and a 3 MB binary per version would bloat the history for
# something reproducible from source. A GitHub release is where a build
# belongs: it hangs off the tag it was built from, so the APK a tester
# installed can always be traced back to the commit that produced it.
#
# Draft by default. A draft is visible only to people who can write to the
# repository, which leaves room to check the APK before anyone can install it;
# pass --publish to make it live immediately.
#
# Usage: npm run release:github            # draft release for the current version
#        npm run release:github -- --publish
set -euo pipefail

cd "$(dirname "$0")/.."

export PATH="$HOME/.local/bin:$PATH"

DRAFT=true
[ "${1:-}" = "--publish" ] && DRAFT=false

if ! command -v gh >/dev/null 2>&1; then
  echo "==> gh is not installed. See pana-mobile/CONFIG.md." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "==> gh is not authenticated. Run: gh auth login" >&2
  exit 1
fi

VERSION="$(node -p "require('./package.json').version")"
TAG="mobile-v${VERSION}"

# Both variants go up together. They are not two grades of the same thing: the
# release APK talks to one compiled-in API over HTTPS, and the debug one can be
# pointed at whatever server the person running it has, which is the only way
# an APK built on this machine is any use to somebody running Pana themselves.
RELEASE_APK="$(ls release/pana-*[0-9].apk 2>/dev/null | grep -v -- '-debug\.apk$' | head -1)"
DEBUG_APK="$(ls release/pana-*-debug.apk 2>/dev/null | head -1)"

if [ -z "$RELEASE_APK" ] || [ -z "$DEBUG_APK" ]; then
  echo "==> Both APKs are needed. Build them with:" >&2
  echo "        npm run release both" >&2
  exit 1
fi

# A release is a tag, and GitHub can only tag a commit it has. Checked here
# rather than left to the API, whose answer to an unknown commit is
# "target_commitish is invalid" -- true, but it does not say to push.
COMMIT="$(git rev-parse HEAD)"
if [ -z "$(git branch -r --contains "$COMMIT" 2>/dev/null)" ]; then
  echo "==> HEAD is not on the remote, so a release has nothing to hang off." >&2
  echo "    Push first:" >&2
  echo "        git push origin $(git branch --show-current)" >&2
  exit 1
fi

# The assets are named for the version rather than left as pana.apk, so a
# downloaded file still says what it is once it is sitting in someone's
# Downloads folder next to every other apk they have.
RELEASE_ASSET="pana-${VERSION}.apk"
DEBUG_ASSET="pana-${VERSION}-debug.apk"
cp "$RELEASE_APK" "release/${RELEASE_ASSET}"
cp "$DEBUG_APK" "release/${DEBUG_ASSET}"

# The signing certificate is what Android checks on every update, so the
# fingerprint is published with the build: someone who wants to know the APK is
# the one we built can compare it against what their phone reports.
APKSIGNER="$(find "$HOME/Android/Sdk/build-tools" -name apksigner | sort -V | tail -1)"
FINGERPRINT="$(
  "$APKSIGNER" verify --print-certs "$RELEASE_APK" 2>/dev/null |
    awk -F': ' '/SHA-256 digest/ {print $2; exit}'
)"

NOTES="$(cat <<EOF
Android build of Pana, version ${VERSION}.

Two APKs, for two different situations.

**\`${RELEASE_ASSET}\`** talks to the hosted Pana API and requires HTTPS.
This is the one to install if you are not running Pana yourself.

**\`${DEBUG_ASSET}\`** lets you enter your own server address on the sign-in
screen, and permits plain HTTP so it can reach an API on your own network.
Install this one if you are running your own Pana backend. It is larger and
slower: it is an unoptimised build, signed with the standard Android debug
key, so Android may warn about the source when you install it.

Only one can be installed at a time. They are signed by different keys, so
Android will not replace one with the other: uninstall before switching.

**Installing:** download the APK and open it on the phone. Android asks for
permission to install from this source the first time; that prompt is about
the app the download came from, not about Pana.

Release build certificate:

\`\`\`
SHA-256: ${FINGERPRINT:-unavailable}
\`\`\`

Built from $(git rev-parse --short HEAD).
EOF
)"

if gh release view "$TAG" >/dev/null 2>&1; then
  echo "==> Release $TAG exists; replacing its APKs"
  gh release upload "$TAG" "release/${RELEASE_ASSET}" "release/${DEBUG_ASSET}" --clobber
else
  echo "==> Creating release $TAG"
  # --target pins the tag to the commit being built rather than to whatever
  # the default branch points at by the time the tag is created.
  gh release create "$TAG" "release/${RELEASE_ASSET}" "release/${DEBUG_ASSET}" \
    --title "Pana ${VERSION} (Android)" \
    --notes "$NOTES" \
    --target "$COMMIT" \
    $([ "$DRAFT" = true ] && echo --draft)
fi

if [ "$DRAFT" = true ]; then
  echo "==> Draft created. Review it, then publish:"
  echo "    gh release edit $TAG --draft=false"
fi

gh release view "$TAG" --json url --jq .url
