#!/usr/bin/env bash
#
# Build and push the pynance-runner container to GHCR.
#
# Usage:
#   ./scripts/build-container.sh              # Build + push, auto-increment version
#   ./scripts/build-container.sh --dry-run    # Build only, no push, no version bump
#   ./scripts/build-container.sh --no-cache   # Force fresh build (no Docker layer cache)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

IMAGE="ghcr.io/cadig/pynance-runner"
VERSION_FILE="$PROJECT_ROOT/docker/VERSION"
DOCKERFILE="$PROJECT_ROOT/docker/Dockerfile"

DRY_RUN=false
NO_CACHE=""

for arg in "$@"; do
    case "$arg" in
        --dry-run)   DRY_RUN=true ;;
        --no-cache)  NO_CACHE="--no-cache" ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--no-cache]"
            echo ""
            echo "  --dry-run    Build only, no push, no version bump"
            echo "  --no-cache   Force fresh Docker build (bypass layer cache)"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Read current version
# ---------------------------------------------------------------------------
if [ ! -f "$VERSION_FILE" ]; then
    echo "ERROR: $VERSION_FILE not found"
    exit 1
fi

VERSION=$(tr -d '[:space:]' < "$VERSION_FILE")
echo "==> Building $IMAGE:$VERSION"

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
build_ok=true
docker build $NO_CACHE \
    -t "$IMAGE:$VERSION" \
    -t "$IMAGE:latest" \
    -f "$DOCKERFILE" \
    "$PROJECT_ROOT/docker" || build_ok=false

if [ "$build_ok" = false ]; then
    echo ""
    echo "ERROR: Docker build failed."
    echo "==> Auto-incrementing version so the next attempt gets a fresh tag."
    # Bump patch version even on failure
    IFS='.' read -r major minor patch <<< "$VERSION"
    NEW_VERSION="$major.$minor.$((patch + 1))"
    echo "$NEW_VERSION" > "$VERSION_FILE"
    echo "==> VERSION bumped: $VERSION -> $NEW_VERSION"
    exit 1
fi

echo ""
echo "==> Build succeeded: $IMAGE:$VERSION"

# ---------------------------------------------------------------------------
# Push (unless --dry-run)
# ---------------------------------------------------------------------------
if [ "$DRY_RUN" = true ]; then
    echo "==> Dry run — skipping push and version bump."
    echo ""
    echo "To test the image locally:"
    echo "  docker run --rm $IMAGE:$VERSION python --version"
    echo "  docker run --rm $IMAGE:$VERSION python -c \"import pandas, numpy, yfinance, anthropic; print('OK')\""
    exit 0
fi

# Verify Docker is logged into GHCR (check config file since --get-login
# is not supported on all Docker versions)
if ! python3 -c "import json; d=json.load(open('$HOME/.docker/config.json')); assert 'ghcr.io' in d.get('auths',{})" 2>/dev/null; then
    echo ""
    echo "ERROR: Not logged into ghcr.io."
    echo "Run:  gh auth token | docker login ghcr.io -u cadig --password-stdin"
    exit 1
fi

echo "==> Pushing $IMAGE:$VERSION ..."
docker push "$IMAGE:$VERSION"

echo "==> Pushing $IMAGE:latest ..."
docker push "$IMAGE:latest"

echo ""
echo "==> Pushed successfully."

# ---------------------------------------------------------------------------
# Bump version for next build
# ---------------------------------------------------------------------------
IFS='.' read -r major minor patch <<< "$VERSION"
NEW_VERSION="$major.$minor.$((patch + 1))"
echo "$NEW_VERSION" > "$VERSION_FILE"
echo "==> VERSION bumped: $VERSION -> $NEW_VERSION"

# ---------------------------------------------------------------------------
# Auto-commit the version bump
# ---------------------------------------------------------------------------
cd "$PROJECT_ROOT"
if git diff --quiet "$VERSION_FILE" 2>/dev/null; then
    echo "==> No version change to commit."
else
    git add "$VERSION_FILE"
    git commit -m "chore: bump container to v$NEW_VERSION"
    echo "==> Committed version bump. Remember to push when ready."
fi

echo ""
echo "Done. Image available at:"
echo "  $IMAGE:$VERSION"
echo "  $IMAGE:latest"
