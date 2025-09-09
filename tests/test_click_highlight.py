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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

module_path = os.path.join(
    os.path.dirname(__file__), "..", "screenvivid", "models", "utils", "transforms.py"
)
spec = importlib.util.spec_from_file_location("screenvivid.models.utils.transforms", module_path)
transforms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transforms)


def test_click_highlight_renders_at_coordinates():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    # Click event at center on frame 0
    click_data = [(0.5, 0.5, 0, "left", "press", 0.0)]
    highlight = transforms.ClickHighlight(
        click_data=click_data, color=(255, 0, 0), radius=5, opacity=1.0, duration=3
    )

    # Frames 0-2 should show highlight
    for f in range(3):
        result = highlight(input=frame.copy(), start_frame=f)
        pixel = result["input"][50, 50]
        # BGR order: red channel index 2
        assert pixel[2] > 0, f"No highlight at frame {f}"

    # After duration, highlight should vanish
    result = highlight(input=frame.copy(), start_frame=3)
    assert (result["input"][50, 50] == [0, 0, 0]).all()
