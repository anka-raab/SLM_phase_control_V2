import tkinter as tk
from tkinter.simpledialog import askstring
from tkinter import ttk
import gxipy as gx
from PIL import Image, ImageTk
import time
import threading
import numpy as np
import os


class CameraControl(object):
    def __init__(self, parent):
        self.cam = None
        self.parent = parent
        self.win = tk.Toplevel()

        title = 'SLM Phase Control - Beam profile'

        self.win.title(title)
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)

        frm_bot = ttk.Frame(self.win)
        frm_mid = ttk.Frame(self.win)

        frm_cam = ttk.Frame(self.win)
        frm_cam_but = ttk.Frame(frm_cam)
        frm_cam_but_set = ttk.Frame(frm_cam_but)

        vcmd = (self.win.register(self.parent.callback))

        but_exit = ttk.Button(frm_bot, text='EXIT', command=self.on_close)
        but_cam_img = ttk.Button(frm_cam_but, text='Initialize', command=self.cam_img)
        but_cam_save = ttk.Button(frm_cam_but, text='Save beam profile', command=self.cam_save)

        lbl_cam_ind = ttk.Label(frm_cam_but_set, text='Camera index:')
        self.strvar_cam_ind = tk.StringVar(self.win, '2')
        self.ent_cam_ind = ttk.Entry(frm_cam_but_set, width=11, validate='all',
                                     validatecommand=(vcmd, '%d', '%P', '%S'),
                                     textvariable=self.strvar_cam_ind)

        lbl_cam_exp = ttk.Label(frm_cam_but_set, text='Camera exposure (µs):')
        self.strvar_cam_exp = tk.StringVar(self.win, '1000')
        self.ent_cam_exp = ttk.Entry(frm_cam_but_set, width=11, validate='all',
                                     validatecommand=(vcmd, '%d', '%P', '%S'),
                                     textvariable=self.strvar_cam_exp)

        lbl_cam_gain = ttk.Label(frm_cam_but_set, text='Camera gain (0-24):')
        self.strvar_cam_gain = tk.StringVar(self.win, '20')
        self.ent_cam_gain = ttk.Entry(frm_cam_but_set, width=11, validate='all',
                                      validatecommand=(vcmd, '%d', '%P', '%S')
                                      , textvariable=self.strvar_cam_gain)

        lbl_cam_time = ttk.Label(frm_cam_but_set, text='Acquisition "time" (1-inf):')
        self.strvar_cam_time = tk.StringVar(self.win, '1000')
        self.ent_cam_time = ttk.Entry(frm_cam_but_set, width=11, validate='all',
                                      validatecommand=(vcmd, '%d', '%P', '%S')
                                      , textvariable=self.strvar_cam_time)

        frm_cam.grid(row=0, column=0, sticky='nsew')
        frm_cam_but.grid(row=1, column=0, sticky='nsew')

        frm_mid.grid(row=2, column=0, sticky='nsew')
        frm_bot.grid(row=3, column=0)

        but_cam_img.grid(row=0, column=0, padx=5, pady=5, ipadx=5, ipady=5)
        but_cam_save.grid(row=0, column=2, padx=5, pady=5, ipadx=5, ipady=5)

        frm_cam_but_set.grid(row=0, column=3, sticky='nsew')
        lbl_cam_ind.grid(row=0, column=0)
        self.ent_cam_ind.grid(row=0, column=1, padx=(0, 10))
        lbl_cam_exp.grid(row=1, column=0)
        self.ent_cam_exp.grid(row=1, column=1, padx=(0, 10))
        lbl_cam_gain.grid(row=2, column=0)
        self.ent_cam_gain.grid(row=2, column=1, padx=(0, 10))
        lbl_cam_time.grid(row=3, column=0)
        self.ent_cam_time.grid(row=3, column=1, padx=(0, 10))

        but_exit.grid(row=1, column=0, padx=5, pady=5, ipadx=5, ipady=5)

        self.img_canvas = tk.Canvas(frm_cam, height=350, width=500)
        self.img_canvas.grid(row=0, sticky='nsew')
        self.img_canvas.configure(bg='grey')
        self.image = self.img_canvas.create_image(0, 0, anchor="nw")

    def init_cam(self):
        print("")
        print("Initializing...")
        print("")

        # create a device manager
        device_manager = gx.DeviceManager()
        dev_num, dev_info_list = device_manager.update_device_list()

        if dev_num == 0:
            print("No connected devices")
            return

        # open the first device
        self.cam = device_manager.open_device_by_index(int(self.ent_cam_ind.get()))

        # set exposure
        self.cam.ExposureTime.set(float(self.ent_cam_exp.get()))

        # set gain
        self.cam.Gain.set(float(self.ent_cam_gain.get()))

        if dev_info_list[0].get("device_class") == gx.GxDeviceClassList.USB2:
            # set trigger mode
            self.cam.TriggerMode.set(gx.GxSwitchEntry.ON)
        else:
            # set trigger mode and trigger source
            self.cam.TriggerMode.set(gx.GxSwitchEntry.ON)
            self.cam.TriggerSource.set(gx.GxTriggerSourceEntry.SOFTWARE)

        # start data acquisition
        self.cam.stream_on()
        print('Streaming...')
        self.acq_mono(int(self.ent_cam_time.get()))
        self.cam.stream_off()
        self.cam.close_device()
        print('...Re-initialisation needed')

    def acq_mono(self, num):
        """
        acquisition function for camera
               :brief      acquisition function of mono device
               :param      num:        number of acquisition images[int]
        """
        for i in range(num):
            time.sleep(0.001)

            # send software trigger command
            self.cam.TriggerSoftware.send_command()

            # set exposure
            self.cam.ExposureTime.set(float(self.ent_cam_exp.get()))

            # set gain
            self.cam.Gain.set(float(self.ent_cam_gain.get()))

            # get raw image
            raw_image = self.cam.data_stream[0].get_image()
            if raw_image is None:
                continue

            # create numpy array with data from raw image
            numpy_image = raw_image.get_numpy_array()
            if numpy_image is None:
                continue

            # Show images
            picture = Image.fromarray(numpy_image)
            picture = ImageTk.PhotoImage(picture)

            self.img_canvas.itemconfig(self.image, image=picture)
            self.img_canvas.image = picture  # keep a reference!

    def cam_save(self):
        # send software trigger command
        self.cam.TriggerSoftware.send_command()

        # get raw image
        raw_image = self.cam.data_stream[0].get_image()
        if raw_image is None:
            print("Getting image failed.")

        # create numpy array with data from raw image
        numpy_image = raw_image.get_numpy_array()
        print(f'Value of the maximum pixel : {np.max(numpy_image)}')

        bmp_image = Image.fromarray(numpy_image)

        file_name = askstring(title="Save As", prompt="Enter a file name (without the extension) :")
        file_name += '.bmp'

        if file_name:
            folder_path = os.path.join(os.getcwd(), "beam_profiles")
            if not os.path.exists(folder_path):
                os.mkdir(folder_path)
            file_path = os.path.join(folder_path, file_name)
            bmp_image.save(file_path)
            print(f"Beam profile saved as {file_path}")
        else:
            print("File save cancelled.")

    def cam_on_close(self):
        self.cam.stream_off()  # stop acquisition
        self.cam.close_device()  # close device

    def cam_img(self):
        self.render_thread = threading.Thread(target=self.init_cam)
        self.render_thread.daemon = True
        self.render_thread.start()

    def on_close(self):
        self.win.destroy()
        self.parent.camera_win = None
