#!/bin/sh
# Copyright 2020 Hewlett Packard Enterprise Development LP

# Wait for the Envoy proxy to be available
until curl --head localhost:15000; \
do
  echo Waiting for proxy sidecar; \
  sleep 3; \
done; \
echo Proxy sidecar available;

# Overwrite content before import
cp -r /shared/* ${CF_IMPORT_CONTENT}/;

# Import the configuration content
python3 /import.py

