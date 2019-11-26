#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tkinter as tk
import random
import socket
from enum import Enum
import os
from PIL import Image
from PIL import ImageTk
from uvctypes import *
import time
import cv2
import numpy as np

try:
    from queue import Queue
except ImportError:
    from Queue import Queue
import platform

if os.name == 'nt':
    from sensor import MotionSenseMock as MotionSense
    from sensor import TempSenseMock as TempSense
    from sensor import BoardMock as Board
else:
    from sensor import Board
    from sensor import TempSense
    from sensor import MotionSense

settings = {
    "use_humidity_sensor": True,
    "display_host_ip": True,
    "display_sleep_timer": True,
    "display_debug_panel": True,
    "sleep_timeout_sec": 10,
    "screen_max_frame_time_sec": 0.033,  # equals to around 30fps
    "ambient_temp_delay_sec": 5
}

BUF_SIZE = 10
q = Queue(BUF_SIZE)


def py_frame_callback(frame, userptr):
    array_pointer = cast(frame.contents.data, POINTER(c_uint16 * (frame.contents.width * frame.contents.height)))
    data = np.frombuffer(
        array_pointer.contents, dtype=np.dtype(np.uint16)
    ).reshape(
        frame.contents.height, frame.contents.width
    )  # no copy

    # data = np.fromiter(
    #   frame.contents.data, dtype=np.dtype(np.uint8), count=frame.contents.data_bytes
    # ).reshape(
    #   frame.contents.height, frame.contents.width, 2
    # ) # copy

    if frame.contents.data_bytes != (2 * frame.contents.width * frame.contents.height):
        return

    if not q.full():
        q.put(data)


PTR_PY_FRAME_CALLBACK = CFUNCTYPE(None, POINTER(uvc_frame), c_void_p)(py_frame_callback)


def ktof(val):
    return (1.8 * ktoc(val) + 32.0)


def ktoc(val):
    return (val - 27315) / 100.0


def raw_to_8bit(data):
    cv2.normalize(data, data, 0, 65535, cv2.NORM_MINMAX)
    np.right_shift(data, 8, data)
    return cv2.cvtColor(np.uint8(data), cv2.COLOR_GRAY2RGB)


def display_temperature(img, val_k, loc, color):
    val = ktof(val_k)
    cv2.putText(img, "{0:.1f} degF".format(val), loc, cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
    x, y = loc
    cv2.line(img, (x - 2, y), (x + 2, y), color, 1)
    cv2.line(img, (x, y - 2), (x, y + 2), color, 1)


class Context():
    def __init__(self):
        self.ctx = POINTER(uvc_context)()
        self.dev = POINTER(uvc_device)()
        self.handle = POINTER(uvc_device_handle)()
        self.ctrl = uvc_stream_ctrl()

    def uvc(self):
        return Uvc(self)


class UvcInitError(Exception):
    pass


class DeviceNotFound(Exception):
    pass


class DeviceNotAvailable(Exception):
    pass


class StreamError(Exception):
    pass


class Uvc():
    def __init__(self, context):
        self.context = context

    def __enter__(self):
        res = libuvc.uvc_init(byref(self.context.ctx), 0)
        if res < 0:
            raise UvcInitError("Failed to initialize UVC")

        return self

    def __exit__(self, *args):
        libuvc.uvc_exit(self.context.ctx)

    def find_device(self):
        res = libuvc.uvc_find_device(self.context.ctx, byref(self.context.dev), PT_USB_VID, PT_USB_PID, 0)
        if res < 0:
            raise DeviceNotFound("Could not find UVC device")

        return

    def open(self):
        self.find_device()
        return Device(self.context)


class Device():
    def __init__(self, context):
        self.context = context

    def __enter__(self):
        res = libuvc.uvc_open(self.context.dev, byref(self.context.handle))
        if res < 0:
            raise DeviceNotAvailable("Failed to open device")

        return self

    def __exit__(self, *args):
        libuvc.uvc_unref_device(self.context.dev)

    def device_info(self):
        print_device_info(self.context.handle)

    def device_formats(self):
        print_device_formats(self.context.handle)

    def stream(self):
        return Stream(self.context)


class Stream():
    def __init__(self, context):
        self.context = context

    def __enter__(self):
        res = libuvc.uvc_start_streaming(self.context.handle, byref(self.context.ctrl), PTR_PY_FRAME_CALLBACK, None, 0)
        if res < 0:
            raise StreamError("Failed to start stream")

        return self

    def __exit__(self, *args):
        libuvc.uvc_stop_streaming(self.context.handle)


class Color(Enum):
    BACKGROUND = "#000"
    FONT_COLOR = "#FFF"
    HEAT_PANEL = "#F00"
    DATA_PANEL = "#0F0"
    DEBUG_PANEL = "#00F"


def get_main_window():
    window = tk.Tk()
    window.title("Smart Mirror GUI")
    window.configure(
        bg=Color.BACKGROUND.value
    )

    window.focus_set()
    window.attributes("-fullscreen", True)
    window.minsize(150, 100)

    return window


def get_ip_address():
    ip_address = ''
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    s.close()
    return ip_address


# CANVAS VERSION
# def get_heat_image_panel(parent):
#     path = "./fire.png"
#     path_ref = cv2.imread(path)
#     cv2_ref = cv2.cvtColor(path_ref, cv2.COLOR_BGR2RGB)
#     img_ref = Image.fromarray(cv2_ref)
#     tk_img_ref = ImageTk.PhotoImage(img_ref)
#
#     heat_image_panel = tk.Canvas(
#         parent,
#         width=480,
#         height=640,
#     )
#     heat_image_panel.create_image(0, 0, image=tk_img_ref)
#     heat_image_panel.place(anchor=tk.NW)
#     return heat_image_panel


# CANVAS VERSION
def get_heat_image_panel(parent):
    path = "./fire.png"
    path_ref = cv2.imread(path)
    cv2_ref = cv2.cvtColor(path_ref, cv2.COLOR_BGR2RGB)
    img_ref = Image.fromarray(cv2_ref)
    tk_img_ref = ImageTk.PhotoImage(img_ref)

    heat_image_panel = tk.Label(
        parent,
        image=tk_img_ref,
        width=480,
        height=640,
    )
    heat_image_panel.image = tk_img_ref
    heat_image_panel.pack(side=tk.TOP, anchor=tk.W)
    return heat_image_panel


def generate_data_labels(parent, data_set):
    string_pointers = {}
    for attr, val in data_set.items():
        string_pointers[attr] = tk.StringVar()
        string_pointers[attr].set('{0}: {1}'.format(attr, str(val)))
        new_label = tk.Label(parent)
        new_label.configure(
            textvariable=string_pointers[attr],
            bg=Color.BACKGROUND.value,
            fg=Color.FONT_COLOR.value,
            width=10,
            anchor=tk.W,
            font=("default", 40)
        )
        new_label.pack()
    return parent, string_pointers


def get_data_panel(parent, data_set):
    data_panel = tk.Frame(parent)
    data_panel.configure(
        bg=Color.DATA_PANEL.value,
        height=10,
    )

    updated_data_panel, string_pointers = generate_data_labels(data_panel, data_set)

    updated_data_panel.pack(side=tk.TOP, anchor=tk.E)
    return updated_data_panel, string_pointers


def get_ambient_temp_data(tmpsensor, last_req_time, last_data_set):
    if time.time() - last_req_time > settings["ambient_temp_delay_sec"]:
        (hum, temp) = tmpsensor.sense()
        hum = round(hum, 2)
        temp = round(temp, 2)

        last_data_set = {"temp": temp, "hum": hum}
        last_req_time = time.time()

    return last_data_set, last_req_time


def update_string_pointers(string_pointers, data_set):
    for attr, pointer in string_pointers.items():
        pointer.set('{0}: {1}'.format(attr, data_set[attr]))


def kill_gui(gui_elements):
    # heat image panel, requires place_remove()
    gui_elements[0].pack_forget()

    # data & debug panel require pack_forget()
    gui_elements[1].pack_forget()
    if settings["display_debug_panel"]:
        gui_elements[2].pack_forget()


def show_gui(gui_elements):
    # heat image panel, requires place_remove()
    gui_elements[0].pack(side=tk.TOP, anchor=tk.W)

    # data & debug panel require pack_forget()
    gui_elements[1].pack(side=tk.TOP, anchor=tk.E)
    if settings["display_debug_panel"]:
        gui_elements[2].pack(side=tk.BOTTOM, anchor=tk.W)


def movement(motion_sensor):
    motion = motion_sensor.sense()
    return motion


def generate_debug_labels(parent):
    string_pointers = {}
    if settings["display_sleep_timer"]:
        string_pointers["display_sleep_timer"] = tk.StringVar()
        string_pointers["display_sleep_timer"].set("Timer: 0")
        timer_label = tk.Label(parent)
        timer_label.configure(
            textvariable=string_pointers["display_sleep_timer"],
            bg=Color.BACKGROUND.value,
            fg=Color.FONT_COLOR.value,
            anchor=tk.W,
            width=40,
            font=("default", 10)
        )
        timer_label.pack()
    if settings["display_host_ip"]:
        ip = get_ip_address()
        string_pointers["display_host_ip"] = tk.StringVar()
        string_pointers["display_host_ip"].set("Mirror network address: {0}".format(ip))
        ip_label = tk.Label(parent)
        ip_label.configure(
            textvariable=string_pointers["display_host_ip"],
            bg=Color.BACKGROUND.value,
            fg=Color.FONT_COLOR.value,
            anchor=tk.W,
            width=40,
            font=("default", 10)
        )
        ip_label.pack()

    return parent, string_pointers


def get_debug_panel(parent):
    debug_panel = tk.Frame(parent)
    debug_panel.configure(
        bg=Color.DEBUG_PANEL.value,
    )
    updated_debug_panel, string_pointers = generate_debug_labels(debug_panel)
    updated_debug_panel.pack(side=tk.BOTTOM, anchor=tk.W)
    return updated_debug_panel, string_pointers


# def update_heat_panel(panel, img):
#     # Use PIL (Pillow) to convert the NumPy ndarray to a PhotoImage
#     im = Image.fromarray(img)
#     photo = ImageTk.PhotoImage(image=im)
#     panel.create_image(0, 0, image=photo, anchor=tk.NW)


if __name__ == '__main__':
    ctx = Context()

    with ctx.uvc() as uvc:
        with uvc.open() as devi:

            devi.device_info()
            devi.device_formats()

            frame_formats = uvc_get_frame_formats_by_guid(devi.context.handle, VS_FMT_GUID_Y16)
            if len(frame_formats) == 0:
                print("device does not support Y16")
                exit(1)

            libuvc.uvc_get_stream_ctrl_format_size(devi.context.handle, byref(devi.context.ctrl), UVC_FRAME_FORMAT_Y16,
                                                   frame_formats[0].wWidth, frame_formats[0].wHeight,
                                                   int(1e7 / frame_formats[0].dwDefaultFrameInterval)
                                                   )

            with devi.stream() as s:
                with Board() as _, MotionSense(7) as motion_sensor, TempSense(17) as ambient_temp_sensor:

                    last_ambient_temp_req_time = 0
                    data_set = 0
                    data_set, last_ambient_temp_req_time = get_ambient_temp_data(
                        ambient_temp_sensor,
                        last_ambient_temp_req_time,
                        data_set
                    )  # return dict for display

                    window = get_main_window()

                    heat_image_panel = get_heat_image_panel(window)
                    data_panel, data_string_pointers = get_data_panel(window, data_set)

                    panels = [
                        heat_image_panel,
                        data_panel
                    ]

                    if settings["display_debug_panel"]:
                        debug_panel, debug_string_pointers = get_debug_panel(window)
                        panels.append(debug_panel)

                    is_gui_shown = True

                    # At boot set start time
                    start_time = time.time()

                    try:
                        while True:
                            # If timer hasn't passed into sleep: ACTIVE
                            time_passed = time.time() - start_time
                            if time_passed < settings["sleep_timeout_sec"]:

                                # GET IMAGE FROM CAMERA
                                # data = q.get(True, 500)
                                # if data is None:
                                #     print("[*] DATA WAS NOONE [*]")
                                #     break
                                # data = cv2.resize(data[:, :], (640, 480))
                                # minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(data)
                                # img = raw_to_8bit(data)
                                # display_temperature(img, minVal, minLoc, (255, 0, 0))
                                # display_temperature(img, maxVal, maxLoc, (0, 0, 255))
                                #
                                # cv_img = Image.fromarray(img)
                                # cv_img = ImageTk.PhotoImage(cv_img)
                                #
                                # heat_image_panel.image = cv_img
                                #
                                # cv2.waitKey(1)

                                # Update data panel
                                data_set, last_ambient_temp_req_time = get_ambient_temp_data(
                                    ambient_temp_sensor,
                                    last_ambient_temp_req_time,
                                    data_set
                                )
                                update_string_pointers(data_string_pointers, data_set)

                                if settings["display_debug_panel"] and settings["display_sleep_timer"]:
                                    time_str = round(time_passed, 1)
                                    timer_str = "Timer: {0} ({1})".format(str(time_str), settings["sleep_timeout_sec"])
                                    debug_string_pointers["display_sleep_timer"].set(timer_str)

                                if movement(motion_sensor):
                                    start_time = time.time()

                            # Else fall into PASSIVE, check for movement
                            else:
                                kill_gui(panels) if is_gui_shown else False
                                # Once movement is detected, show GUI and reset timer
                                if movement(motion_sensor):
                                    show_gui(panels)
                                    start_time = time.time()

                            window.update_idletasks()
                            window.update()

                            time.sleep(settings["screen_max_frame_time_sec"])
                        cv2.destroyAllWindows()
                    except Exception as e:
                        print("[*] EXCEPTION OCCURED [*]")
                        print(e)
