import tkinter as tk
from tkinter import ttk
from pylablib.devices import Andor
import pylablib as pll
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import RectangleSelector
import numpy as np
from tkinter import filedialog
pll.par["devices/dlls/andor_sdk2"] = "andor_driver/"
print('trouvé')


class AndorCameraViewer:
    def __init__(self, master):
        self.master = master
        self.master.title('Andor Camera')

        # Set up the Andor camera
        self.cam = Andor.AndorSDK2Camera(fan_mode="full")
        self.cam.set_exposure(50E-3)
        self.cam.set_acquisition_mode('cont')
        self.cam.setup_shutter("open")
        self.cam.start_acquisition()

        # Create a main frame to group all other frames
        self.main_frame = tk.Frame(self.master)
        self.main_frame.grid(row=0, column=0)

        # Create a frame for the camera display
        self.plot_frame = tk.LabelFrame(self.main_frame, text="Camera display")
        self.fig, self.ax = plt.subplots(figsize=(3, 3))
        self.ax.set_xlabel('Pixels')
        self.ax.set_ylabel('Pixels')
        self.img = self.ax.imshow(self.cam.read_oldest_image())
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().grid(row=1, column=1, padx=0, pady=0, sticky=tk.NSEW)
        self.selector = RectangleSelector(self.ax, self.on_select, useblit=True, button=[1])

        # Create a frame for the sum plot
        self.sum_plot_frame = tk.LabelFrame(self.main_frame, text="Sum over columns")
        self.sum_fig, self.sum_ax = plt.subplots(figsize=(4, 2))
        self.sum_ax.set_xlabel('Pixels')
        self.sum_ax.set_ylabel('Counts')
        self.sum_canvas = FigureCanvasTkAgg(self.sum_fig, master=self.sum_plot_frame)
        self.sum_canvas.get_tk_widget().grid(row=0, column=1, padx=0, pady=0, sticky=tk.NSEW)

        # Create a frame for general settings
        self.settings_frame = tk.Label(self.main_frame)
        self.live_button = tk.Button(master=self.settings_frame, text="Live", command=self.start)
        self.live_button.grid(row=0, column=0, padx=5, pady=5)
        self.stop_button = tk.Button(master=self.settings_frame, text="Stop", command=self.stop)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)
        self.exit_button = tk.Button(master=self.settings_frame, text="Exit", command=self.exit)
        self.exit_button.grid(row=0, column=2, padx=5, pady=5)
        self.save_button = tk.Button(master=self.settings_frame, text="Save image", command=self.save_image)
        self.save_button.grid(row=0, column=3, padx=5, pady=5)

        # Create a frame for the exposure time setting
        self.exposure_frame = tk.LabelFrame(self.main_frame, text="Camera settings")
        self.exposure_label = tk.Label(master=self.exposure_frame, text="Exposure time (s)")
        self.exposure_label.grid(row=0, column=0, padx=5, pady=5)
        self.exposure_time = 50E-3
        self.exposure_time_var = tk.StringVar(value=str(self.exposure_time))
        self.exposure_entry = tk.Entry(master=self.exposure_frame, width=5, textvariable=self.exposure_time_var)
        self.exposure_entry.grid(row=0, column=1, padx=5, pady=5)
        self.exposure_button = tk.Button(master=self.exposure_frame, text="Set exposure time", command=self.set_exposure_time)
        self.exposure_button.grid(row=0, column=2, padx=5, pady=5)

        # Create a frame for the ROI of the image
        self.roi_frame = tk.LabelFrame(self.main_frame, text="Range of interest - XUV camera")
        self.x_start_label = tk.Label(master=self.roi_frame, text="from x =")
        self.x_start_label.grid(row=0, column=0, padx=5, pady=5)
        self.roi_x_start_var = tk.StringVar(value=str(0))
        self.x_start_entry = tk.Entry(master=self.roi_frame, width=10, textvariable=self.roi_x_start_var)
        self.x_start_entry.grid(row=0, column=1, padx=5, pady=5)
        self.x_end_label = tk.Label(master=self.roi_frame, text="to x =")
        self.x_end_label.grid(row=0, column=2, padx=5, pady=5)
        self.roi_x_end_var = tk.StringVar(value=str(self.cam.get_detector_size()[0]))
        self.x_end_entry = tk.Entry(master=self.roi_frame, width=10, textvariable=self.roi_x_end_var)
        self.x_end_entry.grid(row=0, column=3, padx=5, pady=5)
        self.y_start_label = tk.Label(master=self.roi_frame, text="from y =")
        self.y_start_label.grid(row=1, column=0, padx=5, pady=5)
        self.roi_y_start_var = tk.StringVar(value=str(0))
        self.y_start_entry = tk.Entry(master=self.roi_frame, width=10, textvariable=self.roi_y_start_var)
        self.y_start_entry.grid(row=1, column=1, padx=5, pady=5)
        self.y_end_label = tk.Label(master=self.roi_frame, text="to y =")
        self.y_end_label.grid(row=1, column=2, padx=5, pady=5)
        self.roi_y_end_var = tk.StringVar(value=str(self.cam.get_detector_size()[1]))
        self.y_end_entry = tk.Entry(master=self.roi_frame, width=10, textvariable=self.roi_y_end_var)
        self.y_end_entry.grid(row=1, column=3, padx=5, pady=5)
        self.roi_reset_button = tk.Button(master=self.roi_frame, text="Reset image ROI", command=self.reset_roi)
        self.roi_reset_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        self.roi_set_button = tk.Button(master=self.roi_frame, text="Set image ROI", command=self.set_roi)
        self.roi_set_button.grid(row=2, column=2, columnspan=2, padx=5, pady=5)
        self.reset_roi()

        # Create a frame for the summation settings
        self.sum_frame = tk.LabelFrame(self.main_frame, text="Range of interest - Summation plot")
        self.sum_checkbutton = tk.Checkbutton(master=self.sum_frame, text="Show sum plot", variable=tk.BooleanVar(),
                                              command=self.toggle_sum_plot)
        self.sum_checkbutton.grid(row=0, column=0, padx=5, pady=5)
        self.sum_start_var = tk.StringVar(value=str(0))
        self.sum_start_label = tk.Label(master=self.sum_frame, text="from y =")
        self.sum_start_label.grid(row=1, column=0, padx=5, pady=5)
        self.sum_start_entry = tk.Entry(master=self.sum_frame, width=5, textvariable=self.sum_start_var)
        self.sum_start_entry.grid(row=1, column=1, padx=5, pady=5)
        self.sum_end_label = tk.Label(master=self.sum_frame, text="to y =")
        self.sum_end_label.grid(row=1, column=2, padx=5, pady=5)
        self.sum_end_var = tk.StringVar(value=str(self.cam.get_detector_size()[1]))
        self.sum_end_entry = tk.Entry(master=self.sum_frame, width=5, textvariable=self.sum_end_var)
        self.sum_end_entry.grid(row=1, column=3, padx=5, pady=5)
        self.sum_reset_button = tk.Button(master=self.sum_frame, text="Reset sum ROI", command=self.reset_sum_roi)
        self.sum_reset_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        self.sum_set_button = tk.Button(master=self.sum_frame, text="Set sum ROI", command=self.set_sum_roi)
        self.sum_set_button.grid(row=2, column=2, columnspan=2, padx=5, pady=5)
        self.reset_sum_roi()

        # Create a frame for the averaging settings
        self.average_frame = tk.LabelFrame(self.main_frame, text="Averaging settings")
        self.avg_num = 10
        self.avg_checkbutton = tk.Checkbutton(master=self.average_frame, text="Enable averaging", variable=tk.BooleanVar(), command=self.toggle_avg_mode)
        self.avg_checkbutton.grid(row=0, column=0, padx=5, pady=5)
        self.avg_label = tk.Label(master=self.average_frame, text="Number of averages")
        self.avg_label.grid(row=1, column=0, padx=5, pady=5)
        self.avg_var = tk.StringVar(value=str(self.avg_num))
        self.avg_entry = tk.Entry(master=self.average_frame, width=5, textvariable=self.avg_var)
        self.avg_entry.grid(row=1, column=1, padx=5, pady=5)
        self.set_avg_button = tk.Button(master=self.average_frame, text="Set average", command=self.set_avg_num)
        self.set_avg_button.grid(row=0, column=1, padx=5, pady=5)

        # Add all frames to the main frame
        self.plot_frame.grid(row=0, column=0)
        self.sum_plot_frame.grid(row=1, column=0)
        self.settings_frame.grid(row=3, column=0)

        self.roi_frame.grid(row=0, column=1)
        self.sum_frame.grid(row=1, column=1)
        self.exposure_frame.grid(row=2, column=1)
        self.average_frame.grid(row=3, column=1)

        self.sum_start_index = 0
        self.sum_end_index = self.cam.get_detector_size()[1]

        self.live = True
        self.average_mode = False
        self.show_sum_plot = False

    def update_plot(self):
        if self.live:
            self.cam.wait_for_frame()
            frame = self.cam.read_oldest_image()

            # Average over a chosen number of frames
            if self.average_mode:
                frame_sum = frame
                for i in range(self.avg_num - 1):
                    print(f'{i + 1} frames on {self.avg_num}')
                    self.cam.wait_for_frame()
                    frame_sum += self.cam.read_oldest_image()
                frame = frame_sum / self.avg_num

            # Update the first plot
            self.img.set_data(frame)

            if self.ax.images[-1].colorbar is not None:
                self.ax.images[-1].colorbar.remove()
                self.ax.images[-1].colorbar = None

            # Update the second plot if the checkbox is checked
            if self.show_sum_plot:
                sums = np.sum(frame[self.sum_start_index:self.sum_end_index, :], axis=0)
                self.sum_line.set_data(np.arange(len(sums)), sums)
                self.sum_ax.relim()
                self.sum_ax.autoscale_view()

            self.fig.colorbar(self.img)
            self.canvas.draw()
            self.sum_canvas.draw()

            self.master.update_idletasks()
            self.master.after(150, self.update_plot)

    def save_image(self):
        filename = filedialog.asksaveasfilename(defaultextension='.bmp')
        if filename:
            image_array = self.img.get_array()
            plt.imsave(filename, image_array)
            print('Image saved')

    def start(self):
        self.live = True
        self.cam.start_acquisition()
        self.update_plot()
        print('Acquisition started')

    def stop(self):
        self.live = False
        self.cam.stop_acquisition()
        print('Acquisition stopped')

    def toggle_sum_plot(self):
        self.show_sum_plot = not self.show_sum_plot
        if not self.show_sum_plot:
            self.sum_ax.clear()
            self.canvas.draw()
        else:
            self.sum_line, = self.sum_ax.plot([], [])
            self.canvas.draw()

    def toggle_avg_mode(self):
        self.set_avg_num()
        self.average_mode = not self.average_mode
        print('Acquisition mode :', self.cam.get_acquisition_mode())

    def set_avg_num(self):
        new_avg_num = int(self.avg_var.get())
        self.avg_num = new_avg_num
        print('Average number of frames changed')

    def set_exposure_time(self):
        self.cam.stop_acquisition()
        self.cam.set_exposure(self.exposure_entry.get())
        self.cam.start_acquisition()
        print('Exposure time updated')

    def set_roi(self):
        x_start = int(self.roi_x_start_var.get())
        x_end = int(self.roi_x_end_var.get())
        y_start = int(self.roi_y_start_var.get())
        y_end = int(self.roi_y_end_var.get())
        self.cam.set_roi(x_start, x_end, y_start, y_end, hbin=1, vbin=1)

        self.ax.set_xlim(x_start, x_end)
        self.ax.set_ylim(y_start, y_end)

        self.next_frame()
        print('ROI updated')

    def reset_roi(self):

        x_lim = [self.roi_x_start_var.set(str(0)), self.roi_x_end_var.set(str(self.cam.get_detector_size()[0]))]
        y_lim = [self.roi_y_start_var.set(str(0)), self.roi_y_end_var.set(str(self.cam.get_detector_size()[1]))]

        self.ax.set_xlim(x_lim)
        self.ax.set_ylim(y_lim)

        self.set_roi()
        print('ROI set to default')

    def on_select(self, e_click, e_release):
        x1, y1 = int(e_click.xdata), int(e_click.ydata)
        x2, y2 = int(e_release.xdata), int(e_release.ydata)

        self.sum_start_var.set(y1)
        self.sum_end_var.set(y2)

        self.roi_x_start_var.set(x1)
        self.roi_x_end_var.set(x2)
        self.roi_y_start_var.set(y1)
        self.roi_y_end_var.set(y2)

        self.set_sum_roi()
        self.set_roi()

    def set_sum_roi(self):
        self.sum_start_index = int(self.sum_start_var.get())
        self.sum_end_index = int(self.sum_end_var.get())
        print('Sum ROI updated')

    def reset_sum_roi(self):
        self.sum_start_var.set(str(0))
        self.sum_end_var.set(self.cam.get_detector_size()[1])
        self.set_sum_roi()
        print('Sum ROI set to default')

    def next_frame(self):
        self.cam.wait_for_frame()
        frame = self.cam.read_oldest_image()
        self.img.set_data(frame)
        self.canvas.draw()

    def exit(self):
        self.cam.stop_acquisition()
        self.cam.setup_shutter("closed")
        self.cam.close()
        self.master.destroy()
        print('Closing the GUI')


root = tk.Tk()
viewer = AndorCameraViewer(root)
root.mainloop()
