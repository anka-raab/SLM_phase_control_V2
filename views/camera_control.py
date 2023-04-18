import tkinter as tk
import numpy as np
import gxipy as gx
from PIL import Image, ImageTk
import time
import threading


class CameraControl(object):

    def __init__(self, parent, slm_lib):
        self.parent = parent
        self.slm_lib = slm_lib
        self.win = tk.Toplevel()
        self.setpoint = 0

        title = 'SLM Phase Control - Camera control'
        self.win.title(title)
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)
        self.rect_id = 0

        frm_bot = tk.Frame(self.win)

        frm_cam = tk.Frame(self.win)
        frm_cam_but = tk.Frame(frm_cam)
        frm_cam_but_set = tk.Frame(frm_cam_but)

        vcmd = (self.win.register(self.parent.callback))

        but_exit = tk.Button(frm_bot, text='EXIT', command=self.on_close)

        but_cam_img = tk.Button(frm_cam_but, text='Get image', command=self.cam_img)
        lbl_cam_ind = tk.Label(frm_cam_but_set, text='Camera index:')
        self.strvar_cam_ind = tk.StringVar(self.win, '2')
        self.ent_cam_ind = tk.Entry(
            frm_cam_but_set, width=11, validate='all',
            validatecommand=(vcmd, '%d', '%P', '%S'),
            textvariable=self.strvar_cam_ind)
        lbl_cam_exp = tk.Label(frm_cam_but_set, text='Camera exposure (µs):')
        self.strvar_cam_exp = tk.StringVar(self.win, '1000')
        self.ent_cam_exp = tk.Entry(
            frm_cam_but_set, width=11, validate='all',
            validatecommand=(vcmd, '%d', '%P', '%S'),
            textvariable=self.strvar_cam_exp)
        lbl_cam_gain = tk.Label(frm_cam_but_set, text='Camera gain (0-24):')
        self.strvar_cam_gain = tk.StringVar(self.win, '20')
        self.ent_cam_gain = tk.Entry(
            frm_cam_but_set, width=11, validate='all',
            validatecommand=(vcmd, '%d', '%P', '%S'),
            textvariable=self.strvar_cam_gain)

        frm_cam.grid(row=0, column=0, sticky='nsew')
        frm_cam_but.grid(row=1, column=0, sticky='nsew')

        but_cam_img.grid(row=0, column=0, padx=5, pady=5, ipadx=5, ipady=5)
        frm_cam_but_set.grid(row=0, column=3, sticky='nsew')
        lbl_cam_ind.grid(row=0, column=0)
        self.ent_cam_ind.grid(row=0, column=1, padx=(0, 10))
        lbl_cam_exp.grid(row=1, column=0)
        self.ent_cam_exp.grid(row=1, column=1, padx=(0, 10))
        lbl_cam_gain.grid(row=2, column=0)
        self.ent_cam_gain.grid(row=2, column=1, padx=(0, 10))

        but_exit.grid(row=1, column=0, padx=5, pady=5, ipadx=5, ipady=5)

        self.img_canvas = tk.Canvas(frm_cam, height=350, width=500)
        self.img_canvas.grid(row=0, sticky='nsew')
        self.img_canvas.configure(bg='grey')
        self.image = self.img_canvas.create_image(0, 0, anchor="nw")

    def init_cam(self):
        print("")
        print("Initializing......")
        print("")
        # create a device manager
        device_manager = gx.DeviceManager()
        dev_num, dev_info_list = device_manager.update_device_list()
        if dev_num == 0:
            print("Number of enumerated devices is 0")
            return

        # open the first device
        cam1 = device_manager.open_device_by_index(int(self.ent_cam_ind.get()))

        # set exposure
        cam1.ExposureTime.set(float(self.ent_cam_exp.get()))

        # set gain
        cam1.Gain.set(float(self.ent_cam_gain.get()))

        if dev_info_list[0].get("device_class") == gx.GxDeviceClassList.USB2:
            # set trigger mode
            cam1.TriggerMode.set(gx.GxSwitchEntry.ON)
        else:
            # set trigger mode and trigger source
            cam1.TriggerMode.set(gx.GxSwitchEntry.ON)
            cam1.TriggerSource.set(gx.GxTriggerSourceEntry.SOFTWARE)

        # start data acquisition
        cam1.stream_on()
        self.acq_mono(cam1, 10000)
        self.cam_on_close(cam1)

    def acq_mono(self, device, num):
        """
        acquisition function for camera
               :brief      acquisition function of mono device
               :param      device:     device object[Device]
               :param      num:        number of acquisition images[int]
        """
        for i in range(num):
            time.sleep(0.001)

            # send software trigger command
            device.TriggerSoftware.send_command()

            # get raw image
            raw_image = device.data_stream[0].get_image()
            if raw_image is None:
                print("Getting image failed.")
                continue

            # create numpy array with data from raw image
            numpy_image = raw_image.get_numpy_array()
            if numpy_image is None:
                continue

            # # sum to area1
            try:
                xpoints = np.fromstring(self.ent_area1x.get(), sep=',')
                ypoints = np.fromstring(self.ent_area1y.get(), sep=',')
                assert len(xpoints) == len(ypoints) == 2
            except:
                xpoints = np.array([200, 550])
                ypoints = np.array([470, 480])
            if xpoints[1] < xpoints[0]:
                xpoints[1] = xpoints[0] + 2
            if ypoints[1] < ypoints[0]:
                ypoints[1] = ypoints[0] + 2

            # trying spatial phase extraction
            im_ = numpy_image[int(ypoints[0]):int(ypoints[1]), int(xpoints[0]):int(xpoints[1])]
            if self.cbx_dir.get() == 'horizontal':
                self.trace = np.sum(im_, axis=0)
            else:
                self.trace = np.sum(im_, axis=1)

            im_fft = np.fft.fft(self.trace)
            self.abs_im_fft = np.abs(im_fft)
            ind = round(float(self.ent_indexfft.get()))
            try:
                self.im_angl = np.angle(im_fft[ind])
            except:
                self.im_angl = 0
            self.lbl_angle.config(text=np.round(self.im_angl, 6))

            # Show images
            picture = Image.fromarray(numpy_image)
            picture = picture.resize((500, 350), resample=0)
            picture = ImageTk.PhotoImage(picture)

            self.img_canvas.itemconfig(self.image, image=picture)
            self.img_canvas.image = picture  # keep a reference!

            # Draw selection lines
            if self.intvar_area.get() == 1:
                x1, x2 = xpoints * 500 / 1440
                y1, y2 = ypoints * 350 / 1080
                new_rect_id = self.img_canvas.create_rectangle(x1, y1, x2, y2, outline='orange')
                self.img_canvas.delete(self.rect_id)
                self.rect_id = new_rect_id
            else:
                self.img_canvas.delete(self.rect_id)

                # creating the phase vector
            self.im_phase[:-1] = self.im_phase[1:]
            self.im_phase[-1] = self.im_angl

            if self.stop_acquire == 1:
                self.stop_acquire = 0
                break

    def cam_on_close(self, device):
        device.stream_off()  # stop acquisition
        device.close_device()  # close device

    def cam_img(self):
        self.render_thread = threading.Thread(target=self.init_cam)
        self.render_thread.daemon = True
        self.render_thread.start()
        self.plot_phase()

    def on_close(self):
        self.win.destroy()
        self.parent.feedback_win = None
