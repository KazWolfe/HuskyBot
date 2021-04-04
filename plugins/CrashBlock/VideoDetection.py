class VideoDetection:

    # check order:
    # 1. format anomalies (negative duration)
    # 2. stream anomalies
    # 3. frame anomalies (pixel format, resolution change, duration anomalies, timestamp anomalies)

    def frame_pixel_fmt_chk(self):
        """
        Detect video files that have an inconsistent pixel format.

        This method will iterate over each frame of a video file and compare that frame against the pixel_fmt defined
        in the active stream.

        :return: Returns True if the pixel format diverges from the expected value, otherwise False.
        """
        pass

    def frame_resolution_change_chk(self):
        """
        Detect video files that have an inconsistent resolution.

        This method will iterate over each frame of a video file and compare that frame against the width and height
        defined in the active stream.

        Warning - there are legitimate reasons that video files may change resolution. This check may lead to false
        positives in rare cases.

        :return: Returns True of the resolution diverges from the expected value, otherwise False.
        """
        pass

    def format_duration_anomaly_chk(self):
        """
        Detect videos files that have an anomalous duration.

        This method will inspect the video's high-level metadata and check for an implausible duration. Examples include
        videos with a duration of zero, an implausibly high (above hours) duration, or a negative duration.

        Warning - videos with very low framerates may be able to get extremely long lengths without being an implausible
        size, but these videos can generally safely be considered "abusive" and as such will be flagged.

        :return:
        """

