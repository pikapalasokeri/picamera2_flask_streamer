import io
from threading import Condition, Thread
from singleton import Singleton


class StreamingOutput(io.BufferedIOBase):
    # From https://github.com/raspberrypi/picamera2/blob/main/examples/mjpeg_server.py

    def __init__(self):
        self.frame = None
        self.frame_ready_cv = Condition()

    def write(self, buf):
        with self.frame_ready_cv:
            self.frame = buf
            self.frame_ready_cv.notify_all()

    def get(self):
        with self.frame_ready_cv:
            self.frame_ready_cv.wait()
            return self.frame


def _get_camera(resolution_video, resolution_image):
    try:
        from picamera2_wrapper import ReasonablePicameraWrapper

        camera_type = ReasonablePicameraWrapper

    except ModuleNotFoundError as e:
        from laptop_camera import LaptopCamera

        camera_type = LaptopCamera

    return camera_type(resolution_video, resolution_image)


class Camera(metaclass=Singleton):
    def __init__(self, resolution_video=(640, 480), resolution_image=None):
        self._resolution_video = resolution_video
        self._resolution_image = resolution_image

        self._video_stream = StreamingOutput()
        self._image_frame = None
        self._image_requested_cv = Condition()
        self._image_ready_cv = Condition()

        self._thread = Thread(
            target=self._stream,
            kwargs={
                "resolution_video": self._resolution_video,
                "resolution_image": self._resolution_image,
            },
        )
        self._thread.start()

    def get_video_frame(self):
        return self._video_stream.get()

    def get_image_frame(self):
        with self._image_ready_cv:
            with self._image_requested_cv:
                self._image_requested_cv.notify_all()
            self._image_ready_cv.wait()

        return self._image_frame

    def _stream(self, resolution_video, resolution_image):
        with _get_camera(resolution_video, resolution_image) as camera:
            camera.start_recording(self._video_stream)
            while True:
                with self._image_requested_cv:
                    self._image_requested_cv.wait()

                    image_stream = io.BytesIO()
                    camera.capture_file(
                        image_stream,
                        format="jpeg",
                    )

                    with self._image_ready_cv:
                        self._image_frame = image_stream.getvalue()
                        self._image_ready_cv.notify_all()

        self._thread = None
