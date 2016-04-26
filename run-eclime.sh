#!/bin/bash
TIMEOUT=2
KILL_AFTER=1
CMD="/Users/ezra/eclipse/eclim"
if [ `uname` == "Linux" ]; then
    OS="Linux"
    TIMEOUT_CMD="timeout"
elif [ `uname` == "Darwin" ]; then
    OS="Mac"
    TIMEOUT_CMD="/usr/local/bin/gtimeout"
fi
$TIMEOUT_CMD -k $KILL_AFTER $TIMEOUT "$CMD" "$@"
if [ $? -eq 124 ]; then
    echo "Timed out"
    exit 124
fi
