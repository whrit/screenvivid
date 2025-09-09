import sys
import types
import threading
import queue

import numpy as np

# --- minimal cv2 mock -----------------------------------------------------
fake_cv2 = types.SimpleNamespace()

def _resize(img, size, interpolation=None):
    from PIL import Image
    return np.array(Image.fromarray(img).resize(size[::-1], Image.BILINEAR))

def _circle(img, center, radius, color, thickness=-1, lineType=None):
    yy, xx = np.ogrid[:img.shape[0], :img.shape[1]]
    mask = (xx - center[0]) ** 2 + (yy - center[1]) ** 2 <= radius ** 2
    img[mask] = color
    return img

def _addWeighted(a, alpha, b, beta, gamma):
    return (a * alpha + b * beta + gamma).astype(a.dtype)

def _cvtColor(img, code):
    return img[:, :, ::-1]  # bgr <-> rgb swap

def _copyMakeBorder(img, top, bottom, left, right, borderType, dst=None, value=0):
    h, w = img.shape[:2]
    if img.ndim == 2:
        out = np.full((h + top + bottom, w + left + right), value, dtype=img.dtype)
    else:
        out = np.full((h + top + bottom, w + left + right, img.shape[2]), value, dtype=img.dtype)
    out[top:top + h, left:left + w] = img
    return out

def _imread(path, flags=None):
    return np.zeros((16, 16, 4), dtype=np.uint8)

fake_cv2.resize = _resize
fake_cv2.circle = _circle
fake_cv2.addWeighted = _addWeighted
fake_cv2.cvtColor = _cvtColor
fake_cv2.copyMakeBorder = _copyMakeBorder
fake_cv2.imread = _imread
fake_cv2.COLOR_BGR2RGB = 1
fake_cv2.CAP_PROP_POS_FRAMES = 1
fake_cv2.INTER_LINEAR = 1
fake_cv2.LINE_AA = 1
fake_cv2.BORDER_CONSTANT = 0
fake_cv2.IMREAD_UNCHANGED = -1
fake_cv2.INTER_LANCZOS4 = 1

sys.modules["cv2"] = fake_cv2

import os
import importlib
import importlib.util
import types


class DummyVideoCapture:
    def __init__(self, frames):
        self.frames = frames
        self.index = 0

    def read(self):
        if self.index < len(self.frames):
            frame = self.frames[self.index]
            self.index += 1
            return True, frame.copy()
        return False, None

    def set(self, prop, value):
        if prop == fake_cv2.CAP_PROP_POS_FRAMES:
            self.index = int(value)


class DummyVideoProcessor:
    def __init__(self, frames):
        self.video = DummyVideoCapture(frames)
        self.current_frame = 0
        self.start_frame = 0
        self.end_frame = len(frames)
        self.frame_width = frames[0].shape[1]
        self.frame_height = frames[0].shape[0]
        self.fps = 30

        # configuration parameters
        self.padding = 0
        self.border_radius = 0
        self.background = {"type": "color", "value": "#000000"}
        self.cursor_scale = 1.0
        self.highlight_enabled = True
        self.highlight_color = "#ff0000"
        self.highlight_radius = 5
        self.auto_zoom_enabled = False
        self._zoom_factor = 2.0
        self._mouse_events = {}
        self._click_events = [(0.5, 0.5, 0, "left", "press", 0.0)]
        self._zoom_keyframes = {}
        self._cursors_map = {}
        self._x_offset = None
        self._y_offset = None
        self.aspect_ratio = "Auto"
        self._transforms = None


def test_export_renders_click_highlights():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, repo_root)

    screenvivid_pkg = types.ModuleType("screenvivid")
    models_pkg = types.ModuleType("screenvivid.models")
    screenvivid_pkg.models = models_pkg
    sys.modules["screenvivid"] = screenvivid_pkg
    sys.modules["screenvivid.models"] = models_pkg

    utils_root = types.ModuleType("screenvivid.utils")
    sys.modules["screenvivid.utils"] = utils_root

    logging_path = os.path.join(repo_root, "screenvivid", "utils", "logging.py")
    spec_l = importlib.util.spec_from_file_location("screenvivid.utils.logging", logging_path)
    logging_mod = importlib.util.module_from_spec(spec_l)
    spec_l.loader.exec_module(logging_mod)
    utils_root.logging = logging_mod
    sys.modules["screenvivid.utils.logging"] = logging_mod

    general_path = os.path.join(repo_root, "screenvivid", "utils", "general.py")
    spec_g = importlib.util.spec_from_file_location("screenvivid.utils.general", general_path)
    general = importlib.util.module_from_spec(spec_g)
    spec_g.loader.exec_module(general)
    utils_root.general = general
    sys.modules["screenvivid.utils.general"] = general

    transforms_path = os.path.join(repo_root, "screenvivid", "models", "utils", "transforms.py")
    spec_t = importlib.util.spec_from_file_location("screenvivid.models.utils.transforms", transforms_path)
    transforms = importlib.util.module_from_spec(spec_t)
    spec_t.loader.exec_module(transforms)
    utils_pkg = types.ModuleType("screenvivid.models.utils")
    utils_pkg.transforms = transforms
    sys.modules["screenvivid.models.utils"] = utils_pkg
    sys.modules["screenvivid.models.utils.transforms"] = transforms

    export_path = os.path.join(repo_root, "screenvivid", "models", "export.py")
    spec = importlib.util.spec_from_file_location("screenvivid.models.export", export_path)
    export = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(export)

    try:
        frames = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(3)]
        vp = DummyVideoProcessor(frames)

        export_params = {
            "fps": vp.fps,
            "output_size": (vp.frame_width, vp.frame_height),
            "highlight_enabled": True,
            "highlight_color": "#ff0000",
            "highlight_radius": 5,
            "screen_size": (1000, 1000),
            "click_data": vp._click_events,
        }

        q = queue.Queue()
        stop_flag = threading.Event()
        reader = export.VideoReaderThread(vp, q, stop_flag, export_params)
        reader.run()

        out_frames = []
        while True:
            f = q.get()
            if f is None:
                break
            out_frames.append(f)

        assert out_frames, "no frames exported"
        # Click was at center, highlight color converted to RGB -> red channel > 0
        assert out_frames[0][50, 50, 0] > 0
    finally:
        for name in [
            "screenvivid.utils", "screenvivid.utils.logging", "screenvivid.utils.general",
            "screenvivid.models.utils", "screenvivid.models.utils.transforms",
            "screenvivid.models.export",
        ]:
            sys.modules.pop(name, None)
