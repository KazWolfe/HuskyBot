FROM python:3.6.6-alpine

# Set the working directory, and expose a port for Husky
WORKDIR HuskyBot/

# Install prerequisites
RUN apk add --update --virtual .pynacl_deps git build-base python3-dev libffi-dev openssh

# Make and load the keys
ADD keys/* /root/.ssh/
# RUN ssh-keygen
RUN chmod 600 /root/.ssh/id_rsa && \
    echo "StrictHostKeyChecking no " > /root/.ssh/config

# Load in HuskyBot and the latest dependencies
RUN git clone git@github.com:KazWolfe/HuskyBot.git . && \
    python3 -m pip install -r requirements.txt

# Prepare the config volume, we want to have this in its own layer
RUN mkdir -p config/
VOLUME /HuskyBot/config/

# Prepare logs, again in its own layer
RUN mkdir -p logs/
VOLUME /HuskyBot/logs/

# And once everything looks good, launch Husky :3
EXPOSE 9339
ENTRYPOINT ["/usr/local/bin/python3", "HuskyBot.py"]
