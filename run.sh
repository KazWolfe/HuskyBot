#!/usr/bin/env bash

while true; do
    nohup python3 ./BotCore.py 2>>nohup-error.log >/dev/null
done