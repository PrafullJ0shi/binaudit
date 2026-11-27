#!/bin/sh
# Publish web/ to the gh-pages branch, which GitHub Pages serves.
set -e
cd "$(git rev-parse --show-toplevel)"
git subtree split --prefix web -b gh-pages-tmp
git push -f origin gh-pages-tmp:gh-pages
git branch -D gh-pages-tmp
