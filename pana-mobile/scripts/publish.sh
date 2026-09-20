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

APK="release/pana.apk"
if [ ! -f "$APK" ]; then
  echo "==> No APK in release/. Run 'npm run release' first." >&2
  exit 1
fi

VERSION="$(node -p "require('./package.json').version")"
TAG="mobile-v${VERSION}"

# The asset is named for its version rather than left as pana.apk, so a
# downloaded file still says what it is once it is in someone's Downloads
# folder next to every other apk they have.
ASSET="pana-${VERSION}.apk"
cp "$APK" "release/${ASSET}"

# The signing certificate is what Android checks on every update, so the
# fingerprint is published with the build: a tester who wants to know the APK
# is the one we built can compare it against what their phone reports.
FINGERPRINT="$(
  "$(find "$HOME/Android/Sdk/build-tools" -name apksigner | sort -V | tail -1)" \
    verify --print-certs "$APK" 2>/dev/null |
    awk -F': ' '/SHA-256 digest/ {print $2; exit}'
)"

NOTES="$(cat <<EOF
Android build of Pana, version ${VERSION}.

**Install:** download \`${ASSET}\` and open it on the phone. Android asks for
permission to install from this source the first time; that prompt is about
the browser it came from, not about this app.

This build is signed with Pana's own release key. Its certificate fingerprint:

\`\`\`
SHA-256: ${FINGERPRINT:-unavailable}
\`\`\`

Built from $(git rev-parse --short HEAD).
EOF
)"

if gh release view "$TAG" >/dev/null 2>&1; then
  echo "==> Release $TAG exists; replacing its APK"
  gh release upload "$TAG" "release/${ASSET}" --clobber
else
  echo "==> Creating release $TAG"
  # --target pins the tag to the commit being built rather than to whatever
  # the default branch points at by the time the tag is created.
  gh release create "$TAG" "release/${ASSET}" \
    --title "Pana ${VERSION} (Android)" \
    --notes "$NOTES" \
    --target "$(git rev-parse HEAD)" \
    $([ "$DRAFT" = true ] && echo --draft)
fi

if [ "$DRAFT" = true ]; then
  echo "==> Draft created. Review it, then publish:"
  echo "    gh release edit $TAG --draft=false"
fi

gh release view "$TAG" --json url --jq .url
