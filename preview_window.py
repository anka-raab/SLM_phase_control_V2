from settings import slm_size, bit_depth
import numpy as np
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk

matplotlib.use("TkAgg")

print('preview_window in')


class PrevScreen(object):
    """
    A class to create a preview window that displays an initial intensity, the phase that the user
    want to apply and the resulting intensity profile in the focus.

    ...

    Attributes
    ----------
    parent : object
        The parent object that creates the preview window.
    win : tkinter.Toplevel
        The top-level window object that displays the plots.
    fig : matplotlib.figure.Figure
        The figure object that contains the subplots.
    ax1 : matplotlib.axes.Axes
        The subplot object for the input intensity plot.
    ax2 : matplotlib.axes.Axes
        The subplot object for the phase plot.
    ax3 : matplotlib.axes.Axes
        The subplot object for the intensity profile in the focus plot.
    ax4 : matplotlib.axes.Axes
        The subplot object for the intensity plot of the central slice of the
        intensity profile in the focus signal.
    img1 : matplotlib.backends.backend_tkagg.FigureCanvasTkAgg
        The Tkinter-compatible canvas object that displays the figure.
    tk_widget_fig : tkinter.Widget
        The Tkinter widget object that contains the canvas.

    Methods
    -------
    update_plots():
        Updates the data and plots of the figure.
    close_prev():
        Closes the preview window.
    """

    def __init__(self, parent):
        """
        Parameters
        ----------
        parent : object
            The parent object that this window belongs to.
        """
        # Save the parent object
        self.parent = parent
        # Create a new window object
        self.win = tk.Toplevel()
        # Configure the close button to call the close_prev function
        self.win.protocol("WM_DELETE_WINDOW", self.close_prev)
        # Set the title of the window
        self.win.title('SLM Phase Control - Preview')
        # Create a Close button and add it to the window
        btn_close = tk.Button(self.win, text='Close', command=self.close_prev)
        btn_close.grid(row=1)
        # Create a figure object with 4 subplots
        self.fig = Figure(figsize=(6, 5), dpi=100)
        self.ax1 = self.fig.add_subplot(221)
        self.ax2 = self.fig.add_subplot(222)
        self.ax3 = self.fig.add_subplot(223)
        self.ax4 = self.fig.add_subplot(224)
        # Create a FigureCanvasTkAgg object from the figure and add it to the window
        self.img1 = FigureCanvasTkAgg(self.fig, self.win)
        self.tk_widget_fig = self.img1.get_tk_widget()
        self.tk_widget_fig.grid(row=0, sticky='nsew')
        # Call the update_plots function to populate the subplots with data
        self.update_plots()

    def update_plots(self):
        """
        Update the displayed plots with the latest calculated intensity and phase values.

        This method calculates the phase based on the current phase values obtained from the parent object.
        It then applies the input phase to the input intensity and computes the Fourier transform to obtain
        the in-focus intensity. The resulting intensity and phase plots are then displayed in the first and
        second plots, respectively, while the in-focus intensity is displayed in the third plot.
        Finally, a cress-section view of the in-focus intensity is plotted in the fourth plot.
        """
        # Grid creation
        x = np.linspace(-40, 40, slm_size[1])
        y = np.linspace(-30, 30, slm_size[0])
        [X, Y] = np.meshgrid(x, y)
        # Gaussian beam parameters
        x_0 = 0
        y_0 = 0
        w_0 = 15
        A = 1
        res = ((X - x_0) ** 2 + (Y - y_0) ** 2) / (2 * w_0 ** 2)
        input_intensity = A * np.exp(-res)
        # Retrieving the calculated phase
        input_phase = self.parent.get_phase()/bit_depth
        # Applying it to the initial beam
        tmp = abs(np.sqrt(input_intensity))*np.exp(1j*input_phase)
        padded_tmp = np.pad(tmp, 800)
        # Propagation into the focus
        focus_int = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(padded_tmp)))
        f_size = np.divide(focus_int.shape, 2)
        start = int(f_size[1] - 20)
        stop = int(f_size[1] + 20)
        # Plots
        # 1
        self.ax1.clear()
        self.ax1.imshow(input_intensity, cmap='jet', interpolation='None')
        self.ax1.set_title('Before propagation')
        # 2
        self.ax2.clear()
        self.ax2.imshow(np.angle(np.exp(1j * input_phase)), cmap='twilight_shifted', interpolation='None')
        self.ax2.set_title('Phase applied')
        # 3
        self.ax3.clear()
        self.ax3.imshow(abs(focus_int)**2, cmap='jet', interpolation='None')
        self.ax3.set_xlabel('After propagation')
        self.ax3.axis([f_size[1]-40, f_size[1]+40, f_size[0]-30, f_size[0]+30])
        # 4
        self.ax4.clear()
        self.ax4.plot(abs(focus_int[int(f_size[0]), start:stop])**2)
        self.ax4.set_xlabel('Cross-view after propagation')
        self.img1.draw()

    def close_prev(self):
        """
        Close the previous window and notify the parent object.
        """
        self.win.destroy()
        self.parent.prev_win_closed()
