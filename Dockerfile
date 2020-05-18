FROM python:3.7-slim

ENV APPDIR /app

# Install gcc and other core deps used as part of build process
# ToDo: Split this into a multi-stage build (smaller containers)
RUN apt-get update \
    && apt-get install gcc git -y \
    && apt-get clean

# Set the work directory to the application directory.
WORKDIR $APPDIR

# Install requirements and get the base environment ready to go. Use cache-magic so we dont need to redo this
# all the time.
COPY requirements.txt $APPDIR
RUN pip3 install -r $APPDIR/requirements.txt

# Copy the full application from outside the container to inside the container
COPY . $APPDIR

# Expose the management/API port. (future use)
EXPOSE 9339

CMD ["/usr/local/bin/python3", "/app/HuskyBot.py"]