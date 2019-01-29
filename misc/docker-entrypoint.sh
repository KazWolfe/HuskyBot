#!/usr/bin/env sh
set -e

if [[ "$1" = 'HuskyBot.py' ]]; then
    cd /HuskyBot

    # Grab latest husky data
    git fetch
    git reset --hard origin/master
    git pull origin master

    # Update dependencies (if any)
    python3 -m pip install -Ur requirements.txt

    # Run the bot
    exec "/usr/local/bin/python3" $@
else
    exec "$@"
fi