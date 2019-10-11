#!/usr/bin/env sh

echo "$(date +%y.%m.%d)-$(git rev-parse --short HEAD)"