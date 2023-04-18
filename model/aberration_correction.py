from model.settings import slm_size, wavelength, chip_width, chip_height, pixel_size, bit_depth
from model.functions import initial_process, wgs_algo

import numpy as np
import tkinter as tk
from scipy.interpolate import interp2d

from matplotlib import pyplot as plt
from matplotlib import image
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

focal_length = 250e-3  # mm
delta_xy = 3.45e-6

# coordinates in the SLM plane
x_slm = np.linspace(-chip_width / 2, chip_width / 2, slm_size[1])
y_slm = np.linspace(-chip_height / 2, chip_height / 2, slm_size[0])
extent_slm = [x_slm[0] * 1e3, x_slm[-1] * 1e3, y_slm[0] * 1e3, y_slm[-1] * 1e3]

# coordinates in the image plane
x_img = np.fft.fftshift(np.fft.fftfreq(slm_size[1],
                                       pixel_size / (wavelength * focal_length)))
y_img = np.fft.fftshift(np.fft.fftfreq(slm_size[0],
                                       pixel_size / (wavelength * focal_length)))
extent_img = [x_img[0] * 1e3, x_img[-1] * 1e3, y_img[0] * 1e3, y_img[-1] * 1e3]


class AberrationWindow(object):
    """
    A class for creating an aberration window that allows for aberration correction using an SLM phase control system.

    Attributes
    ----------
    parent : object
        The parent object.
    win : tkinter.Toplevel
        The tkinter Toplevel widget for the window.
    vcmd : tkinter.StringVar
        The tkinter StringVar object for validation.
    strvar_wavelength : tkinter.StringVar
        The tkinter StringVar object for wavelength.
    ent_wavelength : tkinter.Entry
        The tkinter Entry widget for wavelength input.
    strvar_f : tkinter.StringVar
        The tkinter StringVar object for focal length.
    ent_f : tkinter.Entry
        The tkinter Entry widget for focal length input.
    strvar_it : tkinter.StringVar
        The tkinter StringVar object for convergence criterion.
    ent_it : tkinter.Entry
        The tkinter Entry widget for convergence criterion input.
    lbl_initial_image_file : tkinter.Label
        The tkinter Label widget for the initial image file.
    lbl_target_image_file : tkinter.Label
        The tkinter Label widget for the target image file.
    tk_widget_fig_initial : matplotlib.backends.backend_tkagg.FigureCanvasTkAgg
        The tkinter canvas widget for the initialisation figure.
    ax1_initialisation : matplotlib.axes._subplots.AxesSubplot
        The matplotlib axes for the initialisation figure.
    ax2_initialisation : matplotlib.axes._subplots.AxesSubplot
        The matplotlib axes for the initialisation figure.
    fig_initialisation : matplotlib.figure.Figure
        The matplotlib figure for the initialisation figure.
    btn_process : tkinter.Button
        The tkinter button for image processing.
    ax1_final : matplotlib.axes._subplots.AxesSubplot
        The matplotlib axes for the final figure.
    ax2_final : matplotlib.axes._subplots.AxesSubplot
        The matplotlib axes for the final figure.
    ax3_final : matplotlib.axes._subplots.AxesSubplot
        The matplotlib axes for the final figure.
    ax4_final : matplotlib.axes._subplots.AxesSubplot
        The matplotlib axes for the final figure.
    fig_final : matplotlib.figure.Figure
        The matplotlib figure for the final figure.
    btn_gen : tkinter.Button
        The tkinter button for generating the phase pattern.

    Methods
    -------
    __init__(self, parent):
        Initializes the AberrationWindow class.
    open_file_initial_image(self):
        Opens a file dialog for selecting the initial image file.
    open_file_target_image(self):
        Opens a file dialog for selecting the target image file.
    image_processing(self):
        Processes the initial and target images and displays them in the initialisation figure.
    calculate_phase(self):
        Calculates the phase pattern for the SLM phase control system.
    close_aberration_window(self):
        Closes the aberration window.
    """
    def __init__(self, parent):
        """
        Initialisation of the AberrationWindow class
        """
        self.parent = parent
        self.win = tk.Toplevel()
        self.win.protocol("WM_DELETE_WINDOW", self.close_aberration_window)
        self.win.title('SLM Phase Control - Aberration correction')
        self.vcmd = (parent.parent.register(parent.callback))

        # Settings frame
        frm_set = tk.LabelFrame(self.win, text='Settings')

        lbl_wavelength = tk.Label(frm_set, text='Wavelength:')
        self.strvar_wavelength = tk.StringVar(value=wavelength)
        self.ent_wavelength = tk.Entry(frm_set, width=10, validate='all', validatecommand=(self.vcmd, '%d', '%P', '%S'),
                                       textvariable=self.strvar_wavelength)

        lbl_f = tk.Label(frm_set, text='focal length [mm]:')
        self.strvar_f = tk.StringVar(value=focal_length * 1e3)
        self.ent_f = tk.Entry(frm_set, width=10, validate='all', validatecommand=(self.vcmd, '%d', '%P', '%S'),
                              textvariable=self.strvar_f)

        lbl_it = tk.Label(frm_set, text='Convergence criterion:')
        self.strvar_it = tk.StringVar(value=0.9999999)
        self.ent_it = tk.Entry(frm_set, width=10, validate='all', validatecommand=(self.vcmd, '%d', '%P', '%S'),
                               textvariable=self.strvar_it)

        lbl_wavelength.grid(row=0, column=0, sticky='e')
        self.ent_wavelength.grid(row=0, column=1, sticky='w')
        lbl_f.grid(row=1, column=0, sticky='e')
        self.ent_f.grid(row=1, column=1, sticky='w')
        lbl_f.grid(row=1, column=0, sticky='e')
        self.ent_f.grid(row=1, column=1, sticky='w')
        lbl_it.grid(row=3, column=0, sticky='e')
        self.ent_it.grid(row=3, column=1, sticky='w')

        # Load initial image frame
        frm_load_initial_image = tk.LabelFrame(self.win, width=300, text='Initial image')
        btn_open_initial_image = tk.Button(frm_load_initial_image, text='Load initial image',
                                           command=self.open_file_initial_image)
        lbl_act_initial_image_file = tk.Label(frm_load_initial_image, text='File containing the initial image :',
                                              justify='left')
        self.lbl_initial_image_file = tk.Label(frm_load_initial_image, text='', wraplength=200, justify='left',
                                               foreground='gray')
        btn_open_initial_image.grid(row=0)
        lbl_act_initial_image_file.grid(row=1)
        self.lbl_initial_image_file.grid(row=2)

        # Load target image frame
        frm_load_target_image = tk.LabelFrame(self.win, width=300, text='Target image')
        btn_open_target_image = tk.Button(frm_load_target_image, text='Load target image',
                                          command=self.open_file_target_image)
        lbl_act_target_image_file = tk.Label(frm_load_target_image, text='File containing the target image :',
                                             justify='left')
        self.lbl_target_image_file = tk.Label(frm_load_target_image, text='', wraplength=200, justify='left',
                                              foreground='gray')
        btn_open_target_image.grid(row=0)
        lbl_act_target_image_file.grid(row=1)
        self.lbl_target_image_file.grid(row=2)

        # Display and process initialisation images
        self.frm_initialisation_display = tk.LabelFrame(self.win, text='Initialisation and process')
        self.btn_process = tk.Button(self.frm_initialisation_display, text='Process and display',
                                     command=self.image_processing)
        plt.rc('font', size=8)

        self.fig_initialisation = Figure(figsize=(5, 2), dpi=100)
        self.ax1_initialisation = self.fig_initialisation.add_subplot(121)
        self.ax1_initialisation.set_title('Initial image at focus', fontsize=8)
        self.ax2_initialisation = self.fig_initialisation.add_subplot(122)
        self.ax2_initialisation.set_title('Target image at focus', fontsize=8)
        self.fig_initialisation.tight_layout()
        self.img_initialisation = FigureCanvasTkAgg(self.fig_initialisation, self.frm_initialisation_display)
        self.tk_widget_fig_initial = self.img_initialisation.get_tk_widget()

        self.btn_process.grid(row=0, column=0, pady=5)
        self.tk_widget_fig_initial.grid(row=1, columnspan=2, sticky='nsew', pady=5)

        # Phase retrieval
        self.frm_calc = tk.LabelFrame(self.win, text='Phase pattern generator')
        self.btn_gen = tk.Button(self.frm_calc, text='Calculate phase', command=self.calculate_phase)

        plt.rc('font', size=8)
        self.fig_final = Figure(figsize=(5, 4), dpi=100)
        self.ax1_final = self.fig_final.add_subplot(221)
        self.ax1_final.set_title('Reconstructed image at focus', fontsize=8)
        self.ax2_final = self.fig_final.add_subplot(222)
        self.ax2_final.set_title('Reconstructed phase at focus', fontsize=8)
        self.ax3_final = self.fig_final.add_subplot(223)
        self.ax3_final.set_title('Reconstructed image at SLM', fontsize=8)
        self.ax4_final = self.fig_final.add_subplot(224)
        self.ax4_final.set_title('Reconstructed phase at SLM (output)', fontsize=8)
        self.fig_final.tight_layout()
        self.img_final = FigureCanvasTkAgg(self.fig_final, self.frm_calc)
        self.tk_widget_fig_final = self.img_final.get_tk_widget()

        self.btn_gen.grid(row=0, column=0, pady=5)
        self.tk_widget_fig_final.grid(row=1, columnspan=2, sticky='nsew', pady=5)

        # Main layout
        btn_ok = tk.Button(self.win, text='OK', command=self.take_pattern)
        btn_close = tk.Button(self.win, text='Close', command=self.close_aberration_window)
        frm_set.grid(row=0, columnspan=2, sticky='nw', padx=5, pady=5)
        frm_load_initial_image.grid(row=1, column=0, sticky='nw', padx=5, pady=5)
        frm_load_target_image.grid(row=1, column=1, sticky='nw', padx=5, pady=5)
        self.frm_initialisation_display.grid(row=2, columnspan=2, sticky='nw', padx=5, pady=5)
        self.frm_calc.grid(row=3, columnspan=2, sticky='nw', padx=5, pady=5)
        btn_ok.grid(row=4, column=0, padx=5, pady=5)
        btn_close.grid(row=4, column=1, padx=5, pady=5)

    def open_file_initial_image(self):
        """
        Opens a file dialog for selecting the initial image file.
        """
        filepath_initial_image = tk.filedialog.askopenfilename(filetypes=[('Image Files', '*.bmp')])

        self.img_initial_image = np.array(image.imread(filepath_initial_image))
        self.lbl_initial_image_file['text'] = f'{filepath_initial_image}'

        self.ax1_initialisation.imshow(self.img_initial_image, cmap='inferno', interpolation='None', extent=extent_img)
        self.img_initialisation.draw()

    def open_file_target_image(self):
        """
        Opens a file dialog for selecting the target image file.
        """
        filepath_target_image = tk.filedialog.askopenfilename(filetypes=[('Image Files', '*.bmp')])

        self.img_target_image = np.array(image.imread(filepath_target_image))
        self.lbl_target_image_file['text'] = f'{filepath_target_image}'

        self.ax2_initialisation.imshow(self.img_target_image, cmap='inferno', interpolation='None', extent=extent_img)
        self.img_initialisation.draw()

    def image_processing(self):
        """
        Processes the initial and target images and displays them in the initialisation figure.
        """
        self.initial_image, _, _ = initial_process(self.img_initial_image, delta_xy)
        self.target_image, _, _ = initial_process(self.img_target_image, delta_xy)
        # XY_plot, XY_prime_plot = utils_plot(cut_x, cut_y, delta_xy, wavelength, focal_length)

        self.ax1_initialisation.imshow(self.initial_image, cmap='inferno', interpolation='None', extent=extent_img)
        self.ax2_initialisation.imshow(self.target_image, cmap='inferno', interpolation='None', extent=extent_img)
        self.img_initialisation.draw()

    def calculate_phase(self):
        """
        Calculate the phase pattern using the Weighted Gerchberg Saxton algorithm.
        """
        crit_convergence = float(self.ent_it.get())

        r_image_focus, r_image_slm, r_phase_focus, r_phase_slm = \
            wgs_algo(self.initial_image, self.target_image, crit_convergence=crit_convergence)

        self.ax1_final.imshow(r_image_focus, cmap='inferno', interpolation='None', extent=extent_img)
        self.ax2_final.imshow(r_phase_focus, cmap='RdBu', interpolation='None', extent=extent_img)
        self.ax3_final.imshow(r_image_slm, cmap='inferno', interpolation='None', extent=extent_slm)
        self.ax4_final.imshow(r_phase_slm, cmap='RdBu', interpolation='None', extent=extent_slm)

        self.pattern_to_resize = r_phase_slm

        self.img_final.draw()

    def take_pattern(self):
        """
        interpolate and send to the main window the retrieved phase pattern.
        """
        # create a 1200 x 1920 grid (slm size)
        x_new = np.linspace(0, 1, 1920)
        y_new = np.linspace(0, 1, 1200)
        interp_func = interp2d(np.linspace(0, 1, 256), np.linspace(0, 1, 256), self.pattern_to_resize, kind='linear')
        self.pattern = interp_func(x_new, y_new)

        self.parent.img = self.pattern / (2 * np.pi) * bit_depth
        print('Ready to publish')

    def close_aberration_window(self):
        """
        Close the aberration control window.
        """
        self.win.destroy()
        self.parent.gen_win = None
