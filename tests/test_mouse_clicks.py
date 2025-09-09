import time
from threading import Thread
from unittest.mock import patch
import types
import sys

import os
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Stub pyautogui to avoid GUI dependencies during tests
fake_pyautogui = types.ModuleType("pyautogui")
fake_pyautogui.position = lambda: (0, 0)
fake_pyautogui.size = lambda: (100, 100)
sys.modules["pyautogui"] = fake_pyautogui

# Stub cursor utilities to avoid heavy dependencies like OpenCV
fake_cursor_module = types.ModuleType("screenvivid.models.utils.cursor")

class DummyCursorLoaderThread:
    def start(self):
        return self

    def get_cursor(self, state):
        return None

    @property
    def cursor_theme(self):
        return {}


def dummy_get_cursor_state(theme):
    return "arrow", {"is_anim": False, "n_steps": 1}

fake_cursor_module.CursorLoaderThread = DummyCursorLoaderThread
fake_cursor_module.get_cursor_state = dummy_get_cursor_state
sys.modules["screenvivid.models.utils.cursor"] = fake_cursor_module

# Stub screen_capture and models package to avoid heavy imports
fake_screen_capture = types.ModuleType("screenvivid.models.screen_capture")

def get_screen_capture_class():
    class DummyCapture:
        def __init__(self, region):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def capture(self):
            return b"", "raw"

    return DummyCapture


fake_screen_capture.get_screen_capture_class = get_screen_capture_class
sys.modules["screenvivid.models.screen_capture"] = fake_screen_capture

fake_models_pkg = types.ModuleType("screenvivid.models")
fake_models_pkg.screen_capture = fake_screen_capture
sys.modules["screenvivid.models"] = fake_models_pkg

import importlib.util

module_path = os.path.join(
    os.path.dirname(__file__), "..", "screenvivid", "models", "screen_recorder.py"
)
spec = importlib.util.spec_from_file_location(
    "screenvivid.models.screen_recorder", module_path
)
screen_recorder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen_recorder)
sys.modules["screenvivid.models.screen_recorder"] = screen_recorder
fake_models_pkg.screen_recorder = screen_recorder
ScreenRecordingThread = screen_recorder.ScreenRecordingThread


class MockButton:
    def __init__(self, name):
        self.name = name


def test_click_events_are_recorded_with_frame_index_and_coordinates():
    recorder = ScreenRecordingThread(output_path="test")
    recorder.set_region([0, 0, 100, 100])
    recorder._device_pixel_ratio = 1.0

    click_cb = {}

    class MockListener:
        def __init__(self, on_click=None, *args, **kwargs):
            click_cb["cb"] = on_click

        def start(self):
            return self

        def stop(self):
            return self

    fake_mouse = types.SimpleNamespace(Listener=MockListener)
    fake_pynput = types.ModuleType("pynput")
    fake_pynput.mouse = fake_mouse

    with patch.dict(sys.modules, {"pynput": fake_pynput, "pynput.mouse": fake_mouse}), patch(
        "screenvivid.models.screen_recorder.pyautogui.position", return_value=(10, 10)
    ), patch.object(ScreenRecordingThread, "_update_fps", lambda self, name: None):
        recorder._is_stopped.clear()
        t = Thread(target=recorder._process_mouse_events)
        t.start()

        # First frame without click
        recorder._frame_index_queue.put(0)
        recorder._frame_timestamps.put(0.1)
        time.sleep(0.05)

        # Emit click between frames
        click_cb["cb"](50, 60, MockButton("left"), True)

        # Second frame processes the click
        recorder._frame_index_queue.put(1)
        recorder._frame_timestamps.put(0.2)
        time.sleep(0.05)

        recorder._is_stopped.set()
        t.join(timeout=1)

    assert len(recorder.mouse_events["click"]) == 1
    event = recorder.mouse_events["click"][0]
    assert event[0] == 0.5  # relative_x
    assert event[1] == 0.6  # relative_y
    assert event[2] == 1  # frame index
    assert event[3] == "left"  # button
    assert event[4] == "press"  # action
    assert event[5] == 0.2  # timestamp from frame

