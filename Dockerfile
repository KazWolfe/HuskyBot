FROM python:3.7.4-alpine

# Set the working directory, and expose a port for Husky
WORKDIR HuskyBot/

# Install prerequisites
RUN apk add --update --virtual .pynacl_deps git build-base python3-dev libffi-dev \
                               openssh postgresql-dev gcc musl-dev jpeg-dev zlib-dev

# Disable SSH strict key checks, just to unbreak things.
RUN mkdir -p /root/.ssh && echo "StrictHostKeyChecking no " > /root/.ssh/config

# Load in HuskyBot and the latest dependencies
RUN git clone https://github.com/KazWolfe/HuskyBot.git . && \
    python3 -m pip install -r requirements.txt

# Prepare the config volume, we want to have this in its own layer
RUN mkdir -p config/
VOLUME /HuskyBot/config/

# Prepare logs, again in its own layer
RUN mkdir -p logs/
VOLUME /HuskyBot/logs/

# Chmod the entrypoint
RUN chmod +x /HuskyBot/misc/docker-entrypoint.sh

# And once everything looks good, launch Husky :3
EXPOSE 9339
ENTRYPOINT ["/HuskyBot/misc/docker-entrypoint.sh"]
CMD ["HuskyBot.py"]
