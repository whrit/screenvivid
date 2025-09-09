import os
import io
import cv2
import queue
import subprocess
import threading
import numpy as np
from PIL import Image
from PySide6.QtCore import Signal, QThread

from screenvivid.models.utils import transforms
from screenvivid.utils.general import get_os_name, get_ffmpeg_path
from screenvivid.utils.logging import logger

class VideoReaderThread(QThread):
    frame_ready = Signal(np.ndarray)

    def __init__(self, video_processor, frame_queue, stop_flag, export_params):
        super().__init__()
        self.video_processor = video_processor
        self.frame_queue = frame_queue
        self.stop_flag = stop_flag
        self.export_params = export_params

        # Build transform pipeline similar to VideoControllerModel
        self.transforms = transforms.Compose({
            "aspect_ratio": transforms.AspectRatio(
                export_params.get("aspect_ratio", "Auto"),
                export_params.get("screen_size", (video_processor.frame_width, video_processor.frame_height)),
            ),
            "auto_zoom": transforms.AutoZoom(
                move_data=export_params.get("move_data", {}),
                zoom_factor=export_params.get("zoom_factor", 2.0),
                keyframes=export_params.get("zoom_keyframes", {}),
            ) if export_params.get("auto_zoom_enabled", False) else transforms.Identity(),
            "click_highlight": transforms.ClickHighlight(
                click_data=export_params.get("click_data", []),
                color=export_params.get("highlight_color"),
                radius=export_params.get("highlight_radius", 20),
            ) if export_params.get("highlight_enabled", False) else transforms.Identity(),
            "cursor": transforms.Cursor(
                move_data=export_params.get("move_data", {}),
                cursors_map=export_params.get("cursors_map", {}),
                offsets=export_params.get("offsets", (None, None)),
                scale=export_params.get("cursor_scale", 1.0),
            ),
            "padding": transforms.Padding(export_params.get("padding", 0)),
            "border_shadow": transforms.BorderShadow(border_radius=export_params.get("border_radius", 0)),
            "background": transforms.Background(export_params.get("background", {"type": "color", "value": "#000000"})),
        })

    def run(self):
        output_size = tuple(self.export_params.get("output_size"))

        current_frame = self.video_processor.current_frame
        self.video_processor.video.set(cv2.CAP_PROP_POS_FRAMES, self.video_processor.start_frame)
        self.video_processor.current_frame = self.video_processor.start_frame

        total_frames = self.video_processor.end_frame - self.video_processor.start_frame
        for _ in range(total_frames):
            if self.stop_flag.is_set():
                break

            ret, frame = self.video_processor.video.read()
            if ret:
                processed_frame = self.transforms(
                    input=frame,
                    start_frame=self.video_processor.start_frame + self.video_processor.current_frame,
                )
                processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                self.video_processor.current_frame += 1

                if processed_frame.shape[:2] != output_size:
                    processed_frame = cv2.resize(processed_frame, output_size)

                self.frame_queue.put(processed_frame)
            else:
                break

        self.video_processor.video.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        self.video_processor.current_frame = current_frame

        self.frame_queue.put(None)

# Codec-specific configurations
codec_params = {
    "mpeg4": {
        "codec": "mpeg4",
        "params": {
            "q:v": "2",         # Highest quality (1-31, lower is better)
            "pix_fmt": "yuv420p",
            "movflags": "+faststart"
        }
    },
    "h264": {
        "codec": "libx264",
        "params": {
            "preset": "medium",  # Slowest preset for best quality
            "crf": "18",           # Very high quality (0-51, lower is better)
            "pix_fmt": "yuv420p",
            "movflags": "+faststart"
        }
    }
}

# Platform-specific overrides and additions
platform_specific = {
    "windows": {
        "default_codec": "h264"
    },
    "macos": {
        "default_codec": "h264"
    },
    "linux": {
        "default_codec": "h264"
    }
}

def get_codec_config(os_name, requested_codec=None):
    """
    Get codec configuration for specified OS and codec.

    Args:
        os_name (str): Operating system name ('windows', 'macos', 'linux')
        requested_codec (str, optional): Specific codec to use. If None, uses h264.

    Returns:
        dict: Combined codec configuration
    """
    # Get platform settings
    platform = platform_specific.get(os_name, {})

    # Determine which codec to use (default to h264 if not specified)
    codec_name = requested_codec if requested_codec in codec_params else "h264"

    # Start with base codec configuration
    config = {
        "codec": codec_params[codec_name]["codec"],
        "params": dict(codec_params[codec_name]["params"])
    }

    # Apply platform-specific codec override if exists
    if codec_name in platform:
        if "codec" in platform[codec_name]:
            config["codec"] = platform[codec_name]["codec"]
        if "params" in platform[codec_name]:
            config["params"].update(platform[codec_name]["params"])

    # Apply platform-specific general params if exists
    if "params" in platform:
        config["params"].update(platform["params"])

    return config

class FFmpegWriterThread(QThread):
    progress = Signal(float)
    finished = Signal()

    def __init__(self, frame_queue, stop_flag, export_params):
        super().__init__()
        self.frame_queue = frame_queue
        self.stop_flag = stop_flag
        self.export_params = export_params

    def _get_ffmpeg_command(self, ffmpeg_path, output_path, fps, output_size, codec_config):
        os_name = get_os_name()
        width, height = output_size
        adjusted_width = (width + 1) & ~1
        adjusted_height = (height + 1) & ~1

        # Get codec configuration from export_params or use default
        requested_codec = self.export_params.get("codec")
        codec_config = get_codec_config(os_name, requested_codec)

        # Allow override of codec parameters from export_params
        if "codec_params" in self.export_params:
            codec_config["params"].update(self.export_params["codec_params"])

        # Base command parameters
        base_cmd = [
            ffmpeg_path,
            '-f', 'image2pipe',
            '-framerate', str(fps),
            '-s', f"{output_size[0]}x{output_size[1]}",
            '-vcodec', 'mjpeg',
            '-i', '-',
            '-vf', f'scale={adjusted_width}:{adjusted_height}'
        ]

        # Build output command from configuration
        output_cmd = ['-c:v', codec_config["codec"]]
        for key, value in codec_config["params"].items():
            output_cmd.extend([f'-{key}', str(value)])

        return base_cmd + output_cmd + ['-y', output_path]

    def run(self):
        format = self.export_params.get("format", "mp4")
        fps = self.export_params.get("fps")
        output_size = tuple(self.export_params.get("output_size"))
        output_file = self.export_params.get("output_path", "output_video")
        icc_profile = self.export_params.get("icc_profile", None)
        total_frames = self.export_params.get("total_frames")
        codec_config = self.export_params.get("codec_config", {})

        # Determine output path
        video_dir = "Videos" if get_os_name() != "macos" else "Movies"
        output_dir = os.path.join(os.path.expanduser("~"), f"{video_dir}/ScreenVivid")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{output_file}.{format}")

        ffmpeg_path = get_ffmpeg_path()

        # FFmpeg command setup - changed pixel format to bgr24
        cmd = self._get_ffmpeg_command(ffmpeg_path, output_path, fps, output_size, codec_config)
        logger.debug(f"FFmpeg export command: {' '.join(cmd)}")

        # Start FFmpeg process with larger pipe buffer
        if get_os_name() == "windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10*1024*1024,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
        else:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10*1024*1024,
            )
        icc_data = None
        try:
            if icc_profile:
                with open(icc_profile, "rb") as f:
                    icc_data = f.read()

            frame_count = 0
            while not self.stop_flag.is_set():
                try:
                    frame = self.frame_queue.get(timeout=0.5)
                    if frame is None:
                        break

                    # Convert frame to PIL Image
                    image = Image.fromarray(frame)

                    # Use context manager for proper buffer cleanup
                    with io.BytesIO() as buffer:
                        try:
                            # Save image to buffer
                            image.save(buffer, format="JPEG", quality=95, icc_profile=icc_data)
                            image_bytes = buffer.getvalue()

                            # Check if process is still running
                            if process.poll() is None:
                                process.stdin.write(image_bytes)
                                process.stdin.flush()
                            else:
                                logger.error("FFmpeg process terminated early.")
                                break

                        except Exception as e:
                            logger.error(f"Error processing frame {frame_count}: {e}")
                            continue
                        finally:
                            # Ensure image is closed to free up memory
                            image.close()

                    frame_count += 1
                    self.progress.emit(frame_count / total_frames * 100)
                    self.frame_queue.task_done()

                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error in write loop: {e}")
                    break

        finally:
            # Proper cleanup
            try:
                if process.poll() is None:
                    process.communicate(b"q")
                    process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
            finally:
                self.finished.emit()


class ExportThread(QThread):
    progress = Signal(float)
    finished = Signal()

    def __init__(self, video_processor, export_params):
        super().__init__()
        self.video_processor = video_processor

        # Make a copy of export parameters and enrich with runtime configuration
        self.export_params = dict(export_params)
        vp = self.video_processor
        self.export_params.setdefault("fps", vp.fps)
        self.export_params.setdefault("output_size", (vp.frame_width, vp.frame_height))
        self.export_params.setdefault("aspect_ratio", vp.aspect_ratio)
        self.export_params.setdefault("padding", vp.padding)
        self.export_params.setdefault("border_radius", vp.border_radius)
        self.export_params.setdefault("background", vp.background)
        self.export_params.setdefault("cursor_scale", vp.cursor_scale)
        self.export_params.setdefault("highlight_enabled", vp.highlight_enabled)
        self.export_params.setdefault("highlight_color", vp.highlight_color)
        self.export_params.setdefault("highlight_radius", vp.highlight_radius)
        self.export_params.setdefault("auto_zoom_enabled", vp.auto_zoom_enabled)
        self.export_params.setdefault("zoom_factor", vp._zoom_factor)
        self.export_params.setdefault("move_data", vp._mouse_events)
        self.export_params.setdefault("click_data", vp._click_events)
        self.export_params.setdefault("zoom_keyframes", vp._zoom_keyframes)
        self.export_params.setdefault("cursors_map", vp._cursors_map)
        self.export_params.setdefault("offsets", (vp._x_offset, vp._y_offset))
        if vp._transforms is not None and vp._transforms.get("aspect_ratio"):
            self.export_params.setdefault("screen_size", vp._transforms["aspect_ratio"].screen_size)
        else:
            self.export_params.setdefault("screen_size", (vp.frame_width, vp.frame_height))

        # Cache cursor positions for quick lookup
        move_data = self.export_params.get("move_data", {})
        if isinstance(move_data, list):
            self.export_params["move_data"] = {i: v for i, v in enumerate(move_data)}

        # Queue used between reader and writer threads
        self.frame_queue = queue.Queue(maxsize=90)
        self._stop_flag = threading.Event()

        self.export_params["total_frames"] = vp.end_frame - vp.start_frame

        self.reader_thread = VideoReaderThread(vp, self.frame_queue, self._stop_flag, self.export_params)
        self.writer_thread = FFmpegWriterThread(self.frame_queue, self._stop_flag, self.export_params)

        self.writer_thread.progress.connect(self.progress.emit)
        self.writer_thread.finished.connect(self.finished.emit)

    def stop(self):
        self._stop_flag.set()
        self.reader_thread.quit()
        self.writer_thread.quit()

    def run(self):
        self.reader_thread.start()
        self.writer_thread.start()

        self.reader_thread.wait()
        self.writer_thread.wait()

        self.finished.emit()
