#!/bin/sh
# Clone the human corpora and the slop tooling at the commits used for the published results.
set -eu
cd "$(dirname "$0")"
mkdir -p sources
fetch() { # name url commit
  if [ -d "sources/$1/.git" ]; then return; fi
  git init -q "sources/$1"
  git -C "sources/$1" fetch -q --depth 1 "$2" "$3"
  git -C "sources/$1" checkout -q FETCH_HEAD
}
fetch peps https://github.com/python/peps.git 545c670f1e986162eb7161d63c944108e504bd09
fetch rfcs https://github.com/rust-lang/rfcs.git d2705ad64ba47e812a2b6b19d6f613fb4c14c5e0
fetch slop-score https://github.com/sam-paech/slop-score.git 289264ab2a0df1358ef81ced3c259610ea709514
fetch slop-forensics https://github.com/sam-paech/slop-forensics.git c313f042620f027d49101da3256bd306b628071a
echo "sources ready"
