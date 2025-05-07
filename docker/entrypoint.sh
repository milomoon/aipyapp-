#!/bin/sh

if [ "$1" = "--ttyd" ]; then
    shift
    ttyd -p 80 -W uv run aipy "$@"
else
    uv run aipy "$@"
fi
