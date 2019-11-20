import tkinter as tk
from time import sleep
import random
from enum import Enum

import sys
#sys.path.append('/home/pi/smart_mirror/screen/sensor')
from sensor import Board, TempSense, MotionSense 

class Color(Enum):
    BACKGROUND = "#000"
    FONT_COLOR = "#FFF"
    HEAT_PANEL = "#F00"
    DATA_PANEL = "#0F0"





def get_main_window():
    window = tk.Tk()
    window.title("Smart Mirror GUI")
    window.configure(
        bg=Color.BACKGROUND.value
    )
    window.geometry('600x1000')

#    window.wm_state("zoomed")

    # def fullscreen_toggle(top_window, event="none"):
    #     top_window.focus_set()
    #     top_window.overrideredirect(True)
    #
    #     top_window.attributes("-fullscreen", True)
    #     top_window.wm_attributes("-topmost", 1)
    #
    # def fullscreen_cancel(top_window, event="none"):
    #     top_window.overrideredirect(False)
    #     top_window.attributes("-fullscreen", False)
    #     top_window.wm_attributes("-topmost", 0)
    #
    #     top_window.centerWindow()


    # TODO: fill full screen
    # window.bind("<F11>", fullscreen_toggle)
    # window.bind("<Escape>", fullscreen_cancel)
    #
    # window.fullscreen_toggle()

    window.minsize(150, 100)
    # window.wm_state("zoomed")

    #window.focus_set()
    # window.overrideredirect(True)

    #window.attributes("-fullscreen", True)
    #window.wm_attributes("-topmost", 1)

    return window


def get_heat_image_panel(parent):
    heat_image_panel = tk.Frame(parent)
    heat_image_panel.configure(
        bg=Color.HEAT_PANEL.value,
    )
    heat_image_panel.place(relwidth=0.2, relheight=0.2, anchor=tk.NW)

    # TODO add video stream

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
            anchor=tk.E,
            font=("default", 40)
        )
        new_label.pack()
    return parent, string_pointers


def get_data_panel(parent, data_set):
    data_panel = tk.Frame(parent)
    data_panel.configure(
        bg=Color.DATA_PANEL.value,
    )
    data_panel.place(relwidth=0.3, relheight=0.2, anchor=tk.NE)

    updated_data_panel, string_pointers = generate_data_labels(parent, data_set)

    return updated_data_panel, string_pointers


def get_mock_data():
    return {
        "temp": random.randint(1, 101),
        "hum": random.randint(1, 101),
    }


def get_data(tmpsensor, motionsensor):
    (hum, temp) = tmpsensor.sense()
    hum = round(hum, 2)
    temp = round(temp, 2)
    motion = motionsensor.sense()
    return {"temp": temp, "hum": hum, "motion": motion }

def update_string_pointers(string_pointers, data_set):
    for attr, pointer in string_pointers.items():
        pointer.set('{0}: {1}'.format(attr, data_set[attr]))


if __name__ == '__main__':
    with Board() as board, MotionSense(7) as motion, TempSense(17) as temp:
        data_set = get_mock_data()

        window = get_main_window()

        heat_image_panel = get_heat_image_panel(window)
        data_panel, string_pointers = get_data_panel(window, data_set)

        while(True):
            data_set = get_mock_data()

            update_string_pointers(string_pointers, data_set)

            window.update_idletasks()
            window.update()

           # sleep(0.1)
           # sleep(0.033)  # equals to around 30fps
