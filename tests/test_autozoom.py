import os
import sys
import importlib.util

import numpy as np
import types

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

fake_cv2.resize = _resize
fake_cv2.circle = _circle
fake_cv2.addWeighted = _addWeighted
fake_cv2.INTER_LINEAR = 1
fake_cv2.LINE_AA = 1

sys.modules.setdefault("cv2", fake_cv2)

# Import transforms module directly from source tree
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

module_path = os.path.join(
    os.path.dirname(__file__), "..", "screenvivid", "models", "utils", "transforms.py"
)
spec = importlib.util.spec_from_file_location(
    "screenvivid.models.utils.transforms", module_path
)
transforms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transforms)


def _gradient_frame(width: int, height: int):
    """Create a frame encoding x in red and y in green channels."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :, 2] = np.tile(np.arange(width, dtype=np.uint8), (height, 1))
    frame[:, :, 1] = np.tile(np.arange(height, dtype=np.uint8).reshape(height, 1), (1, width))
    return frame


def test_autozoom_crops_and_clamps():
    frame = _gradient_frame(100, 100)
    move_data = {0: (0.8, 0.5, 0, "", 0)}

    zoom = transforms.AutoZoom(
        move_data=move_data, zoom_factor=2.0, pan_speed=1.0, smoothing=1.0, edge_margin=0
    )
    result = zoom(input=frame.copy(), start_frame=0)["input"]
    center_pixel = result[50, 50]

    # Expected center after clamping near right edge is roughly (75, 50)
    assert abs(int(center_pixel[2]) - 75) <= 1  # red channel encodes x
    assert abs(int(center_pixel[1]) - 50) <= 1  # green channel encodes y


def test_autozoom_smoothing_behavior():
    frame = _gradient_frame(100, 100)
    move_data = {
        0: (0.2, 0.2, 0, "", 0),
        1: (0.8, 0.8, 0, "", 0),
    }

    zoom = transforms.AutoZoom(
        move_data=move_data, zoom_factor=2.0, pan_speed=0.5, smoothing=1.0, edge_margin=0
    )

    out0 = zoom(input=frame.copy(), start_frame=0)["input"]
    center0 = out0[50, 50]
    assert abs(int(center0[2]) - 35) <= 1

    out1 = zoom(input=frame.copy(), start_frame=1)["input"]
    center1 = out1[50, 50]
    assert abs(int(center1[2]) - 57) <= 1
    # Ensure smoothing prevented jumping directly to target (80)
    assert center1[2] < 70

