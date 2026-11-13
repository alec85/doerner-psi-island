#!/usr/bin/env bash
# Install Wine with 32-bit support and a virtual X display (Xvfb) so that the
# Delphi original can run headless on Linux (Ubuntu/Debian, x86_64).
# Needs root. Idempotent: safe to run again.
set -euo pipefail

if ! dpkg --print-foreign-architectures | grep -qx i386; then
  dpkg --add-architecture i386
fi
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
  wine wine32:i386 wine64 xvfb xdotool x11-utils imagemagick xauth >/dev/null

wine --version
