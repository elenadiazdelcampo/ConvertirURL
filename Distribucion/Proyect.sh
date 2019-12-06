#!/bin/sh

echo "--------------------Preparando proyecto--------------------"
mkdir -p /tmp/db/registry
mkdir -p /tmp/db/node1
mkdir -p /tmp/db/node2
mkdir -p /tmp/db/node3
mkdir -p /tmp/db/youtube
cp ../downloader.ice /tmp/db/youtube
cp ../Servant.py /tmp/db/youtube
cp ../SyncTimer.py /tmp/db/youtube
cp ../Library.py /tmp/db/youtube
icepatch2calc /tmp/db/youtube
