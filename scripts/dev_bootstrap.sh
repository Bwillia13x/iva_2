#!/usr/bin/env bash
set -e
make dev
make playwright
echo "Bootstrap complete."
