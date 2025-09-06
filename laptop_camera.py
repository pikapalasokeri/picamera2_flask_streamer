#!/usr/bin/env python3

from threading import Thread

import cv2

import framerate


class LaptopCamera:
    # The idea is that this class exposes the important functionality from picamera in
    # order to make it easy to prototype and debug without the real raspi hardware.

    def __init__(self, resolution_video=(640, 480), resolution_image=None):
        self._resolution_video = resolution_video
        self._resolution_image = resolution_image

    def __enter__(self):
        if self._resolution_image is None:
            self._resolution_image = (1024, 768)

        self._vc = cv2.VideoCapture(0)
        self._rval = False
        if self._vc.isOpened():
            self._rval, _ = self._vc.read()
        else:
            raise RuntimeError("Could not open VideoCapture.")
        self._thread = None
        return self

    def __exit__(self):
        self._vc.release()

    def capture_file(
        self,
        stream,
        format,
    ):
        rval, frame = self._vc.read()
        frame = cv2.resize(frame, self._resolution_image)
        encoded_frame = cv2.imencode(f".{format}", frame)[1]
        stream.write(encoded_frame.tobytes())
        print("capture() encoded frame shape:", encoded_frame.shape)

    def start_recording(self, stream):
        self._thread = Thread(
            target=self._recording_thread,
            kwargs={
                "stream": stream,
                "format": "jpeg",
            },
        )
        self._thread.start()

    def capture_continuous(self, stream, format):
        while self._rval:
            rval, frame = self._vc.read()
            frame = cv2.resize(frame, self._resolution_image)
            encoded_frame = cv2.imencode(f".{format}", frame)[1]

            print("capture_continuous() encoded frame shape:", encoded_frame.shape)

            stream.write(encoded_frame.tobytes())
            yield None

    def _recording_thread(self, stream, format):
        for foo in self.capture_continuous(stream, format):
            framerate.sleep()
