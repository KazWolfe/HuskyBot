
FFPROBE_COMMAND = ["/usr/bin/ffprobe",
                   "-print_format json",
                   "-show_format",
                   "-show_streams",
                   "-show_frames",
                   "-loglevel quiet"]


class FFProbeShim:
    def __init__(self, filename):
        self.filename = filename

