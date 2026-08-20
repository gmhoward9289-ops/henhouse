#!/usr/bin/env bash
# Read-only: does PyPI serve the version henhouse claims?
set -u

OWNER=gmhoward9289-ops
REPO=$OWNER/henhouse
DIST=henhouse
ROOT=$(cd "$(dirname "$0")/.." && pwd)
GRACE_MIN=${PUBLISH_DOCTOR_GRACE_MIN:-60}
if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi

VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/pyproject.toml" | head -1)
if [ -z "$VERSION" ]; then
  echo "FATAL: could not read version from pyproject.toml" >&2
  exit 2
fi

fails=0; pendings=0; todos=0
say()  { printf '  %-8s %-10s %s\n' "$1" "$2" "$3"; }
pass() { say PASS "$1" "$2"; }
skip() { say "--" "$1" "$2"; }
todo() { say TODO "$1" "$2"; todos=$((todos + 1)); }
pend() { say PENDING "$1" "$2"; pendings=$((pendings + 1)); }
fail() { say FAIL "$1" "$2"; fails=$((fails + 1)); }
lagging() { if [ "$fresh" = 1 ]; then pend "$1" "$2 [$why_fresh]"; else fail "$1" "$2"; fi; }

echo "henhouse publish doctor -- version $VERSION (read-only)"
echo

published=$(gh release view "v$VERSION" --repo "$REPO" --json publishedAt --jq '.publishedAt' 2>/dev/null)
if [ -n "${published:-}" ]; then
  age_min=$("$PY" -c 'import datetime,sys; t=datetime.datetime.strptime(sys.argv[1],"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc); print(int((datetime.datetime.now(datetime.timezone.utc)-t).total_seconds()//60))' "$published" 2>/dev/null)
  : "${age_min:=99999}"
  [ "$age_min" -lt "$GRACE_MIN" ] && fresh=1 || fresh=0
  why_fresh="release is ${age_min}m old, inside the ${GRACE_MIN}m window"
else
  fresh=1
  why_fresh="no v$VERSION GitHub release yet (optional)"
fi

tags=$(gh api "repos/$REPO/git/refs/tags" --jq '.[].ref' 2>/dev/null | sed 's#refs/tags/##')
latest_tag=$(printf '%s\n' "$tags" | grep -v '^$' | sed 's/^v//' | sort -V | tail -1)
if printf '%s\n' "$tags" | grep -qx "v$VERSION"; then pass "git tag" "v$VERSION on remote"
elif [ -z "${latest_tag:-}" ]; then todo "git tag" "no tags yet"
elif [ "$(printf '%s\n%s\n' "$latest_tag" "$VERSION" | sort -V | tail -1)" = "$VERSION" ]; then pend "git tag" "newest v$latest_tag, code says $VERSION"
else fail "git tag" "remote v$latest_tag but code says $VERSION"; fi

pypi=$(curl -sf "https://pypi.org/pypi/$DIST/json" 2>/dev/null)
if [ -z "$pypi" ]; then
  todo pypi "nothing on PyPI -- pending publisher (owner $OWNER, repo henhouse, workflow release.yml, environment pypi)"
else
  pypi_ver=$(printf '%s' "$pypi" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["info"]["version"])' 2>/dev/null)
  if [ "${pypi_ver:-}" = "$VERSION" ]; then
    names=$(printf '%s' "$pypi" | "$PY" -c 'import json,sys; print(" ".join(f["filename"] for f in json.load(sys.stdin)["urls"]))' 2>/dev/null)
    case " $names " in *" henhouse-$VERSION-py3-none-any.whl "*) ;; *) fail pypi "missing wheel for $VERSION" ;; esac
    case " $names " in *" henhouse-$VERSION.tar.gz "*) ;; *) fail pypi "missing sdist for $VERSION" ;; esac
    pass pypi "pip install $DIST ($pypi_ver)"
  else
    lagging pypi "registry has ${pypi_ver:-?}, want $VERSION"
  fi
fi

echo
printf 'pending %d  todo %d  fail %d\n' "$pendings" "$todos" "$fails"
[ "$fails" -ne 0 ] && exit 1
echo "PyPI matches $VERSION (or nothing established yet)."
