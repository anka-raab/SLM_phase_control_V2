# -*- coding: utf-8 -*-
"""
Created on Mon Feb 27 13:09:32 2023

@author: atto
"""

from settings import SANTEC_SLM, slm_size, bit_depth
import tkinter as tk
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import pyplot as plt
import matplotlib
matplotlib.use("TkAgg")
import avaspec_driver._avs_py as avs
import gxipy as gx
from PIL import Image, ImageTk
import time
import draw_polygon
from simple_pid import PID
import threading
from pynput import keyboard
from datetime import date
from os.path import exists

import sys
sys.path.insert(0, "C:/Users/atto/camera_git/Vimba_6.0/VimbaPython/Source/")

import cv2
from vimba import *

class feedbacker(object):
    """works back and forth with publish_window"""

    def __init__(self, parent, slm_lib, CAMERA):
        self.CAMERA = CAMERA   # True for Camera Mode, False for Spectrometer Mode
        self.parent = parent
        self.slm_lib = slm_lib
        self.win = tk.Toplevel()
        self.setpoint = 0
        if self.CAMERA: 
            title = 'SLM Phase Control - Feedbacker (spatial)'
        else:
            title = 'SLM Phase Control - Feedbacker (spectral)'
        self.win.title(title)
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)
        if not SANTEC_SLM:
            self.win.geometry('500x950+300+100')
        self.rect_id = 0

        # creating frames
        frm_bot = tk.Frame(self.win)
        frm_plt = tk.Frame(self.win)
        frm_mid = tk.Frame(self.win)
        if self.CAMERA:
            frm_cam = tk.Frame(self.win)
            frm_cam_but = tk.Frame(frm_cam)
            frm_cam_but_set = tk.Frame(frm_cam_but)
        else:
            frm_spc_but = tk.Frame(self.win)
            frm_spc_but_set = tk.Frame(frm_spc_but)
            frm_plt_set = tk.LabelFrame(frm_mid, text='Plot options')
        frm_ratio = tk.LabelFrame(frm_mid, text='Phase extraction')
        frm_pid = tk.LabelFrame(frm_mid, text='PID controller')
        
        frm_meas = tk.LabelFrame(frm_mid, text='Proper Phase Scan')

        
        vcmd = (self.win.register(self.parent.callback))

        # creating buttons n labels
        but_exit = tk.Button(frm_bot, text='EXIT', command=self.on_close)
        but_feedback = tk.Button(frm_bot, text='Feedback', command=self.feedback)
        if self.CAMERA:
            but_cam_img = tk.Button(frm_cam_but, text='Get image', command=self.cam_img)
            but_cam_line = tk.Button(frm_cam_but, text='Plot fft', command=self.plot_fft)
            but_cam_phi = tk.Button(frm_cam_but, text='scan 2pi fast', command=self.fast_scan)
            lbl_cam_ind = tk.Label(frm_cam_but_set, text='Camera index:')
            self.strvar_cam_ind = tk.StringVar(self.win,'2')
            self.ent_cam_ind = tk.Entry(
                frm_cam_but_set, width=11,  validate='all',
                validatecommand=(vcmd, '%d', '%P', '%S'),
                textvariable=self.strvar_cam_ind)
            lbl_cam_exp = tk.Label(frm_cam_but_set, text='Camera exposure (µs):')
            self.strvar_cam_exp = tk.StringVar(self.win,'1000')
            self.ent_cam_exp = tk.Entry(
                frm_cam_but_set, width=11,  validate='all',
                validatecommand=(vcmd, '%d', '%P', '%S'),
                textvariable=self.strvar_cam_exp)
            lbl_cam_gain = tk.Label(frm_cam_but_set, text='Camera gain (0-24):')
            self.strvar_cam_gain = tk.StringVar(self.win,'20')
            self.ent_cam_gain = tk.Entry(
                frm_cam_but_set, width=11,  validate='all',
                validatecommand=(vcmd, '%d', '%P', '%S'),
                textvariable=self.strvar_cam_gain)
        else:
            lbl_spc_ind = tk.Label(frm_spc_but_set, text='Spectrometer index:')
            self.strvar_spc_ind = tk.StringVar(self.win,'1')
            self.ent_spc_ind = tk.Entry(
                frm_spc_but_set, width=9,  validate='all',
                validatecommand=(vcmd, '%d', '%P', '%S'),
                textvariable=self.strvar_spc_ind)
            lbl_spc_exp = tk.Label(frm_spc_but_set, text='Exposure time (ms):')
            self.strvar_spc_exp = tk.StringVar(self.win,'50')
            self.ent_spc_exp = tk.Entry(
                frm_spc_but_set, width=9,  validate='all',
                validatecommand=(vcmd, '%d', '%P', '%S'),
                textvariable=self.strvar_spc_exp)
            lbl_spc_gain = tk.Label(frm_spc_but_set, text='Nr. of averages:')
            self.strvar_spc_avg = tk.StringVar(self.win,'1')
            self.ent_spc_avg = tk.Entry(
                frm_spc_but_set, width=9,  validate='all',
                validatecommand=(vcmd, '%d', '%P', '%S'),
                textvariable=self.strvar_spc_avg)
            but_spc_activate = tk.Button(frm_spc_but_set, text='Activate',
                                    command=self.spec_activate, width=8)
            but_spc_deactivate = tk.Button(frm_spc_but_set, text='Deactivate',
                                    command=self.spec_deactivate, width=8)
            but_spc_start = tk.Button(frm_spc_but, text='Start\nSpectrometer',
                                      command=self.spc_img, height=2)
            but_spc_stop = tk.Button(frm_spc_but, text='Stop\nSpectrometer',
                                     command=self.stop_measure, height=2)
            but_spc_phi = tk.Button(frm_spc_but, text='fast 2pi',
                                    command=self.fast_scan, height=2)     
            but_auto_scale = tk.Button(frm_plt_set, text='auto-scale',
                                    command=self.auto_scale_spec_axis, width=13)
            but_bck = tk.Button(frm_plt_set, text='take background',
                                    command=self.take_background, width=13)
            lbl_std = tk.Label(frm_plt_set, text='sigma:', width=6)
            self.lbl_std_val = tk.Label(frm_plt_set, text='None', width=6)
        lbl_phi = tk.Label(frm_ratio, text='Phase shift:')
        lbl_phi_2 = tk.Label(frm_ratio, text='pi')
        self.strvar_flat = tk.StringVar()
        self.ent_flat = tk.Entry(
            frm_ratio, width=11,  validate='all',
            validatecommand=(vcmd, '%d', '%P', '%S'),
            textvariable=self.strvar_flat)
        if SANTEC_SLM: text='4'
        else: text='8'
        if not CAMERA: text='17'
        self.strvar_indexfft = tk.StringVar(self.win,text)
        lbl_indexfft = tk.Label(frm_ratio, text='Index fft:')
        lbl_angle = tk.Label(frm_ratio, text='Phase:')
        self.ent_indexfft = tk.Entry(
            frm_ratio, width=11,
            textvariable=self.strvar_indexfft)
        self.lbl_angle = tk.Label(frm_ratio, text='angle')
        if SANTEC_SLM: text='400, 1050'
        else: text='255, 420'
        if not CAMERA: text = '1950'
        self.strvar_area1x = tk.StringVar(self.win,text)
        self.ent_area1x = tk.Entry(
            frm_ratio, width=11,
            textvariable=self.strvar_area1x)
        if SANTEC_SLM: text='630, 650'
        else: text='470, 480'
        if not CAMERA: text = '2100'
        self.strvar_area1y = tk.StringVar(self.win,text)
        self.ent_area1y = tk.Entry(
            frm_ratio, width=11,
            textvariable=self.strvar_area1y)
        if self.CAMERA:
            self.intvar_area = tk.IntVar()
            self.cbox_area = tk.Checkbutton(frm_ratio, text='view area',
                               variable=self.intvar_area,
                               onvalue=1, offvalue=0)
            lbl_direction = tk.Label(frm_ratio, text='Integration direction:')
            self.cbx_dir = tk.ttk.Combobox(frm_ratio, width=10,
                                           values=['horizontal', 'vertical'])
            self.cbx_dir.current(0)
            
            
        lbl_setp = tk.Label(frm_pid, text='Setpoint:')
        self.strvar_setp = tk.StringVar(self.win,'0')
        self.ent_setp = tk.Entry(
            frm_pid, width=11,  validate='all',
            validatecommand=(vcmd, '%d', '%P', '%S'),
            textvariable=self.strvar_setp)
        lbl_pidp = tk.Label(frm_pid, text='P-value:')
        self.strvar_pidp = tk.StringVar(self.win,'-0.2')
        self.ent_pidp = tk.Entry(
            frm_pid, width=11,  validate='all',
            validatecommand=(vcmd, '%d', '%P', '%S'),
            textvariable=self.strvar_pidp)
        lbl_pidi = tk.Label(frm_pid, text='I-value:')
        self.strvar_pidi = tk.StringVar(self.win,'-0.8')
        self.ent_pidi = tk.Entry(
            frm_pid, width=11,  validate='all',
            validatecommand=(vcmd, '%d', '%P', '%S'),
            textvariable=self.strvar_pidi)
        but_pid_setp = tk.Button(frm_pid, text='Setpoint', command=self.set_setpoint)
        but_pid_enbl = tk.Button(frm_pid, text='Start PID', command=self.enbl_pid)
        but_pid_stop = tk.Button(frm_pid, text='Stop PID', command=self.pid_stop)
        but_pid_setk = tk.Button(frm_pid, text='Set PID values', command=self.set_pid_val)



        lbl_from = tk.Label(frm_meas, text='From:')
        self.strvar_from = tk.StringVar(self.win,'-2.6')
        self.ent_from = tk.Entry(
            frm_meas, width=5,  validate='all',
            validatecommand=(vcmd, '%d', '%P', '%S'),
            textvariable=self.strvar_from)
        lbl_to = tk.Label(frm_meas, text='To:')
        self.strvar_to = tk.StringVar(self.win,'2.6')
        self.ent_to = tk.Entry(
            frm_meas, width=5,  validate='all',
            validatecommand=(vcmd, '%d', '%P', '%S'),
            textvariable=self.strvar_to)
        lbl_steps = tk.Label(frm_meas, text='Steps:')
        self.strvar_steps = tk.StringVar(self.win,'10')
        self.ent_steps = tk.Entry(
            frm_meas, width=5,  validate='all',
            validatecommand=(vcmd, '%d', '%P', '%S'),
            textvariable=self.strvar_steps)     
        lbl_avgs = tk.Label(frm_meas, text='Avgs:')
        self.strvar_avgs = tk.StringVar(self.win,'5')
        self.ent_avgs = tk.Entry(
            frm_meas, width=5,  validate='all',
            validatecommand=(vcmd, '%d', '%P', '%S'),
            textvariable=self.strvar_avgs)     


        lbl_comment = tk.Label(frm_meas, text='comment:')
        self.strvar_comment = tk.StringVar(self.win, ' ')
        self.ent_comment = tk.Entry(
            frm_meas, width=10,  validate='none',
            textvariable=self.strvar_comment)     


        but_meas_scan = tk.Button(frm_meas, text='Measure + Save', command=self.enabl_mcp)
        but_meas_simple = tk.Button(frm_meas, text='Single_Image', command=self.enabl_mcp_simple)


        # setting up
        if self.CAMERA:
            frm_cam.grid(row=0, column=0, sticky='nsew')
            frm_cam_but.grid(row=1, column=0, sticky='nsew')
        else:
            frm_spc_but.grid(row=0, column=0, sticky='nsew')
            
        frm_plt.grid(row=1, column=0, sticky='nsew')
        frm_mid.grid(row=2, column=0, sticky='nsew')
        frm_bot.grid(row=3, column=0)
        if self.CAMERA:
            frm_ratio.grid(row=0, column=0, padx=5)
            frm_pid.grid(row=0, column=1, padx=5)
            frm_ratio.config(width=282, height=108)
        else:
            frm_plt_set.grid(row=0, column=0, padx=5)
            frm_ratio.grid(row=0, column=1, padx=5)
            frm_pid.grid(row=0, column=2, padx=5)
            frm_meas.grid(row=0, column=3, padx=5)

            frm_ratio.config(width=162, height=104)
            
        frm_ratio.grid_propagate(False)

        # setting up buttons frm_cam / frm_spc
        if self.CAMERA:
            but_cam_img.grid(row=0, column=0, padx=5, pady=5, ipadx=5, ipady=5)
            but_cam_line.grid(row=0, column=1, padx=5, pady=5, ipadx=5, ipady=5)
            but_cam_phi.grid(row=0, column=2, padx=5, pady=5, ipadx=5, ipady=5)
            frm_cam_but_set.grid(row=0, column=3, sticky='nsew')
            lbl_cam_ind.grid(row=0, column=0)
            self.ent_cam_ind.grid(row=0, column=1, padx=(0,10))
            lbl_cam_exp.grid(row=1, column=0)
            self.ent_cam_exp.grid(row=1, column=1, padx=(0,10))
            lbl_cam_gain.grid(row=2, column=0)
            self.ent_cam_gain.grid(row=2, column=1, padx=(0,10))
        else:
            frm_spc_but_set.grid(row=0, column=0, sticky='nsew')
            but_spc_start.grid(row=0, column=1, padx=5, pady=5, ipadx=5, ipady=5)
            but_spc_stop.grid(row=0, column=2, padx=5, pady=5, ipadx=5, ipady=5)
            but_spc_phi.grid(row=0, column=3, padx=5, pady=5, ipadx=5, ipady=5)
            lbl_spc_ind.grid(row=0, column=0)
            self.ent_spc_ind.grid(row=0, column=1)
            but_spc_activate.grid(row=0, column=2, padx=(1,5))
            lbl_spc_exp.grid(row=1, column=0)
            self.ent_spc_exp.grid(row=1, column=1)
            but_spc_deactivate.grid(row=1, column=2, padx=(1,5))
            lbl_spc_gain.grid(row=2, column=0)
            self.ent_spc_avg.grid(row=2, column=1)
        
        # setting up frm_spc_set
        if not self.CAMERA:
            but_auto_scale.grid(row=0, column=0, columnspan=2, padx=5, pady=(3,10))
            but_bck.grid(row=1, column=0, columnspan=2, padx=5)
            lbl_std.grid(row=2, column=0, pady=5)
            self.lbl_std_val.grid(row=2, column=1, pady=5)

        # setting up buttons frm_bot
        but_exit.grid(row=1, column=0, padx=5, pady=5, ipadx=5, ipady=5)
        but_feedback.grid(row=1, column=1, padx=5, pady=5, ipadx=5, ipady=5)

        # setting up frm_pid
        lbl_setp.grid(row=0, column=0)
        lbl_pidp.grid(row=1, column=0)
        lbl_pidi.grid(row=2, column=0)
        self.ent_setp.grid(row=0, column=1)
        self.ent_pidp.grid(row=1, column=1)
        self.ent_pidi.grid(row=2, column=1)
        but_pid_setp.grid(row=3, column=0)
        but_pid_setk.grid(row=3, column=1)
        but_pid_enbl.grid(row=1, column=2)
        but_pid_stop.grid(row=2, column=2)
        
        
        # setting up frm_meas
        lbl_from.grid(row=0, column=0)
        lbl_to.grid(row=1, column=0)
        lbl_steps.grid(row=2, column=0)
        lbl_avgs.grid(row=3, column=0)
        lbl_comment.grid(row=4, column=0)
        self.ent_from.grid(row=0, column=1)
        self.ent_to.grid(row=1, column=1)
        self.ent_steps.grid(row=2, column=1)
        self.ent_avgs.grid(row=3, column=1)
        self.ent_comment.grid(row=4, column=1)

        but_meas_scan.grid(row=5, column=0)
        but_meas_simple.grid(row=5, column=1)

        
        # setting up cam image
        if self.CAMERA:
            self.img_canvas = tk.Canvas(frm_cam, height=350, width=500)
            self.img_canvas.grid(row=0, sticky='nsew')
            self.img_canvas.configure(bg='grey')
            self.image = self.img_canvas.create_image(0, 0, anchor="nw")

        # setting up frm_plt
        if self.CAMERA: sizefactor = 1
        else: sizefactor = 1.05
        
        self.figr = Figure(figsize=(5*sizefactor, 2*sizefactor), dpi=100)
        self.ax1r = self.figr.add_subplot(211)
        self.ax2r = self.figr.add_subplot(212)
        self.trace_line, = self.ax1r.plot([])
        self.fourier_line, = self.ax2r.plot([])
        self.fourier_indicator = self.ax2r.plot([], 'v')[0]
        self.fourier_text = self.ax2r.text(0.4,0.5, "")
        self.ax1r.set_xlim(0, 200)
        self.ax1r.set_ylim(0, 3000)
        self.ax1r.grid()
        self.ax2r.set_xlim(0, 50)
        self.ax2r.set_ylim(0, .6)
        self.figr.canvas.draw()
        self.img1r = FigureCanvasTkAgg(self.figr, frm_plt)
        self.tk_widget_figr = self.img1r.get_tk_widget()
        self.tk_widget_figr.grid(row=0, column=0, sticky='nsew')
        self.img1r.draw()
        self.ax1r_blit = self.figr.canvas.copy_from_bbox(self.ax1r.bbox)
        self.ax2r_blit = self.figr.canvas.copy_from_bbox(self.ax2r.bbox)
        
        self.figp = Figure(figsize=(5*sizefactor, 2*sizefactor), dpi=100)
        self.ax1p = self.figp.add_subplot(111)
        self.phase_line, = self.ax1p.plot([], '.', ms=1)
        self.ax1p.set_xlim(0, 1000)
        self.ax1p.set_ylim([-np.pi, np.pi])
        self.ax1p.grid()
        self.figp.canvas.draw()
        self.img1p = FigureCanvasTkAgg(self.figp, frm_plt)
        self.tk_widget_figp = self.img1p.get_tk_widget()
        self.tk_widget_figp.grid(row=1, column=0, sticky='nsew')
        self.img1p.draw()
        self.ax1p_blit = self.figp.canvas.copy_from_bbox(self.ax1p.bbox)

        # setting up frm_ratio
        self.ent_area1x.grid(row=0, column=0)
        self.ent_area1y.grid(row=0, column=1)
        if self.CAMERA:
            self.cbox_area.grid(row=0, column=2)
            lbl_direction.grid(row=1, column=0, columnspan=2)
            self.cbx_dir.grid(row=1, column=2, columnspan=2, sticky='w')
            lbl_indexfft.grid(row=2, column=0, sticky='e')
            self.ent_indexfft.grid(row=2, column=1)
            lbl_angle.grid(row=2, column=2)
            self.lbl_angle.grid(row=2, column=3)
            lbl_phi.grid(row=3, column=0, sticky='e')
            self.ent_flat.grid(row=3, column=1)
            lbl_phi_2.grid(row=3, column=2, sticky='w')
        else:
            lbl_indexfft.grid(row=1, column=0, sticky='e')
            self.ent_indexfft.grid(row=1, column=1)
            lbl_angle.grid(row=2, column=0)
            self.lbl_angle.grid(row=2, column=1)
            lbl_phi.grid(row=3, column=0, sticky='e')
            self.ent_flat.grid(row=3, column=1)
            lbl_phi_2.grid(row=3, column=2, sticky='w')

        self.im_phase = np.zeros(1000)
        self.pid = PID(0.35, 0, 0, setpoint=0)

        # setting up a listener for catchin esc from cam1 or spec
        self.stop_acquire = 0
        global stop_pid
        stop_pid = False
        l = keyboard.Listener(on_press=self.press_callback)
        l.start()
        # class attributes to store spectrometer state
        if not self.CAMERA:
            self.spec_interface_initialized = False
            self.active_spec_handle = None

   
    def enabl_mcp(self):
        global stop_mcp
        stop_mcp=False
        self.mcp_thread = threading.Thread(target=self.measure)
        self.mcp_thread.daemon = True
        self.mcp_thread.start()


    def enabl_mcp_simple(self):
        global stop_mcp
        stop_mcp=False
        self.mcp_thread = threading.Thread(target=self.measure_simple)
        self.mcp_thread.daemon = True
        self.mcp_thread.start()

    def measure(self):
        print("now I am measuring",float(self.ent_from.get()))
        
        name = 'C:/data/'+ str(date.today())+'/'+str(date.today()) + '-' + 'auto-log.txt'
        if exists(name):
            print("a log file already exists!")
            lines = np.loadtxt(name, comments="#", delimiter="\t", unpack=False)
            f= open(name,"a+")
            print(lines.shape)
            #last_line = f.readlines()[-1]
            start_image=lines[-1,0] +1
            print("The last image had index " + str(int(start_image-1)))
        else:
            f= open(name,"a+")
            start_image = 0
        
        f.write("# "+ " from: " +str(self.ent_from.get()) + " to: " + str(self.ent_to.get()) + " Steps: " + str(self.ent_steps.get()) + " avgs: " + str(self.ent_avgs.get()) +str(self.ent_comment.get())+"\n")
        self.phis = np.linspace(float(self.ent_from.get()),float(self.ent_to.get()),int(self.ent_steps.get()))
        
        print("getting to scan starting point...")
        self.strvar_setp.set(self.phis[0])
        self.set_setpoint()
        time.sleep(3)
        print("Ready to scan!")
        
        for ind,phi in enumerate(self.phis):
            self.strvar_setp.set(phi)
            self.set_setpoint()
            with Vimba.get_instance() as vimba:
                cams = vimba.get_all_cameras()
                image = np.zeros([1000, 1600])
                start_time = time.time()
                
                nr =  int(self.ent_avgs.get())
                
                with cams[0] as cam:
                    for frame in cam.get_frame_generator(limit = int(self.ent_avgs.get())):
                       frame = cam.get_frame()
                       frame.convert_pixel_format(PixelFormat.Mono8)
                       img = frame.as_opencv_image()
                       img = np.squeeze(frame.as_opencv_image())
                       numpy_image = img
                       image = image + numpy_image
                    image = image/nr
                    end_time = time.time()
                    elapsed_time = end_time - start_time
                    filename = 'C:/data/'+ str(date.today())+'/'+str(date.today()) + '-' + str(int(start_image+ind+1)) + '.bmp'
                    cv2.imwrite(filename, image)
                    print("Phase: ", round(phi,2)," Elapsed time: ", round(elapsed_time,2)) 
                    f.write(str(int(start_image+ind))+"\t"+str(round(phi,2))+"\n")
        f.close()
        return image
    
    
    def measure_simple(self):
        print("now I am measuring one simple image")
        
        name = 'C:/data/'+ str(date.today())+'/'+str(date.today()) + '-' + 'auto-log.txt'
        if exists(name):
            print("a log file already exists!")
            lines = np.loadtxt(name, comments="#", delimiter="\t", unpack=False)
            f= open(name,"a+")
            print(lines.shape)
            #last_line = f.readlines()[-1]
            start_image=lines[-1,0] +1
            print("The last image had index " + str(int(start_image-1)))
        else:
            f= open(name,"a+")
            start_image = 0
        
        f.write("# simple measurement, "+ " avgs: " + str(self.ent_avgs.get()) +str(self.ent_comment.get())+"\n")
     
        with Vimba.get_instance() as vimba:
          cams = vimba.get_all_cameras()
          image = np.zeros([1000, 1600])
          start_time = time.time()
                
          nr =  int(self.ent_avgs.get())
          with cams[0] as cam:
              for frame in cam.get_frame_generator(limit = int(self.ent_avgs.get())):
                  frame = cam.get_frame()
                  frame.convert_pixel_format(PixelFormat.Mono8)
                  img = frame.as_opencv_image()
                  img = np.squeeze(frame.as_opencv_image())
                  numpy_image = img
                  image = image + numpy_image
              image = image/nr
              end_time = time.time()
              elapsed_time = end_time - start_time
              filename = 'C:/data/'+ str(date.today())+'/'+str(date.today()) + '-' + str(int(start_image+1)) + '.bmp'
              cv2.imwrite(filename, image)
              print("simple image taken, Elapsed time: ", round(elapsed_time,2)) 
              f.write(str(int(start_image))+"\n")
              f.close()
        return image

    def press_callback(self, key): 
        if key == keyboard.Key.esc:
            self.stop_acquire = 1
        return

    def feedback(self):
        if self.ent_flat.get() != '':
            phi = float(self.ent_flat.get())
        else:
            phi = 0
        phase_map = self.parent.phase_map + phi/2*bit_depth
        if SANTEC_SLM:
            self.slm_lib.SLM_Disp_Open(int(self.parent.ent_scr.get()))
            self.slm_lib.SLM_Disp_Data(int(self.parent.ent_scr.get()), phase_map,
                                          slm_size[1], slm_size[0])
        else:
            self.parent.pub_win.publish_img(phase_map)

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
                if SANTEC_SLM:
                    xpoints = np.array([400, 1050])
                    ypoints = np.array([630, 650])
                else:
                    xpoints = np.array([200, 550])
                    ypoints = np.array([470, 480])
            if xpoints[1] < xpoints[0]:
                xpoints[1] = xpoints[0]+2
            if ypoints[1] < ypoints[0]:
                ypoints[1] = ypoints[0]+2

            #trying spatial phase extraction
            im_ = numpy_image[int(ypoints[0]):int(ypoints[1]),int(xpoints[0]):int(xpoints[1])]
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
            self.img_canvas.image = picture # keep a reference!
            
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
    
    
    def eval_spec(self):
        """
        acquisition function for spectrometer
               :brief      acquisition function of mono device
               :param      num:        number of acquisition images[int]
        """
        while True:
            time.sleep(0.01)

            # get raw trace
            timestamp, data = avs.get_spectrum(self.active_spec_handle)

            start = int(self.ent_area1x.get())
            stop = int(self.ent_area1y.get())
            self.trace = data[start:stop]
            
            #print(timestamp)

            im_fft = np.fft.fft(self.trace)
            self.abs_im_fft = np.abs(im_fft)
            self.abs_im_fft = self.abs_im_fft / np.max(self.abs_im_fft)
            ind = round(float(self.ent_indexfft.get()))
            try:
                self.im_angl = np.angle(im_fft[ind])
            except:
                self.im_angl = 0
            self.lbl_angle.config(text=np.round(self.im_angl, 6))

            # creating the phase vector
            self.im_phase[:-1] = self.im_phase[1:]
            self.im_phase[-1] = self.im_angl
            
            # calculating standard deviation
            mean = np.mean(self.im_phase)
            std = np.sqrt(np.sum((self.im_phase-mean)**2) / (len(self.im_phase)-1))
            self.lbl_std_val.config(text=np.round(std, 4))

            if self.stop_acquire == 1:
                self.stop_acquire = 0
                break
            
            self.plot_fft_blit()


    def cam_on_close(self, device):
        device.stream_off()   # stop acquisition
        device.close_device()   # close device

    def cam_img(self):
        self.render_thread = threading.Thread(target=self.init_cam)
        self.render_thread.daemon = True
        self.render_thread.start()
        self.plot_phase()

    def spc_img(self):
        self.render_thread = threading.Thread(target=self.start_measure)
        self.render_thread.daemon = True
        self.render_thread.start()
        self.plot_phase()
        
    def take_background(self):
        if not hasattr(self, 'trace'):
            raise AttributeError('Take a spectrum to be used as background')
        self.background = self.trace
        
    def auto_scale_spec_axis(self):
        # this may take ~200ms, do not add it to the mainloop!
        if not hasattr(self, 'trace'):
            raise AttributeError('Take a spectrum before trying autoscale')
        self.ax1r.clear()
        self.trace_line, = self.ax1r.plot([])
        self.ax1r.set_xlim(0, len(self.trace))
        self.ax1r.set_ylim(0, np.max(self.trace)*1.2)
        self.ax1r.grid('both')
        self.figr.canvas.draw()
        self.img1r.draw()
        self.ax1r_blit = self.figr.canvas.copy_from_bbox(self.ax1r.bbox)
        
    def plot_fft(self):
        # find maximum in the fourier trace
        maxindex = np.where(self.abs_im_fft == np.max(self.abs_im_fft[3:50]))[0][0]
        print(maxindex)
        
        self.ax1r.clear()
        self.ax1r.plot(self.trace)
        self.ax2r.clear()
        self.ax2r.plot(self.abs_im_fft)
        self.ax2r.plot(maxindex, self.abs_im_fft[maxindex]*1.2, 'v')
        self.ax2r.text(maxindex-1, self.abs_im_fft[maxindex]*1.5, str(maxindex))
        self.ax2r.set_xlim(0,50)
        self.img1r.draw()

    def plot_fft_blit(self):
        # find maximum in the fourier trace
        maxindex = np.where(self.abs_im_fft == np.max(self.abs_im_fft[5:50]))[0][0]
        
        self.figr.canvas.restore_region(self.ax1r_blit)
        self.figr.canvas.restore_region(self.ax2r_blit)
        self.trace_line.set_data(np.arange(len(self.trace)), self.trace)
        self.ax1r.draw_artist(self.trace_line)
        self.fourier_line.set_data(np.arange(50), self.abs_im_fft[:50])
        self.ax1r.draw_artist(self.fourier_line)
        self.fourier_indicator.set_data([maxindex], [self.abs_im_fft[maxindex]+0.05])
        self.ax1r.draw_artist(self.fourier_indicator)
        self.fourier_text.set_text(str(maxindex))
        self.fourier_text.set_position((maxindex-1, self.abs_im_fft[maxindex]+0.09))
        self.ax1r.draw_artist(self.fourier_text)
        self.figr.canvas.blit()
        self.figr.canvas.flush_events()

    def plot_phase(self):
        self.figp.canvas.restore_region(self.ax1p_blit)
        self.phase_line.set_data(np.arange(1000), self.im_phase)
        self.ax1p.draw_artist(self.phase_line)
        self.figp.canvas.blit(self.ax1p.bbox)
        self.figp.canvas.flush_events()
        self.win.after(50,self.plot_phase)

    
    def spec_activate(self):
        if not self.spec_interface_initialized:
            avs.AVS_Init()
        if self.active_spec_handle is None:
            speclist = avs.AVS_GetList()
            print(str(len(speclist)) + ' spectrometer(s) found.')
            self.active_spec_handle = avs.AVS_Activate(speclist[0])
            self.ent_spc_ind.config(state='disabled')

    def spec_deactivate(self):
        if self.active_spec_handle is not None:
            avs.AVS_StopMeasure(self.active_spec_handle)
            avs.AVS_Deactivate(self.active_spec_handle)
            self.ent_spc_ind.config(state='normal')
            self.active_spec_handle = None
    
    def start_measure(self):
        self.spec_activate()
        int_time = float(self.ent_spc_exp.get())
        no_avg = int(self.ent_spc_avg.get())
        avs.set_measure_params(self.active_spec_handle, int_time, no_avg)
        avs.AVS_Measure(self.active_spec_handle)
        self.eval_spec()
    
    def stop_measure(self):
        if self.active_spec_handle is not None:
            avs.AVS_StopMeasure(self.active_spec_handle)

    def fast_scan(self):
        self.phis = np.linspace(0,2*np.pi,60)
        self.phi_ind = 0
        self.fast_scan_loop()

    def fast_scan_loop(self):
        self.strvar_setp.set(self.phis[self.phi_ind])
        self.set_setpoint()
        self.phi_ind = self.phi_ind + 1
        if self.phi_ind < 60:
            self.win.after(100, self.fast_scan_loop)

    def set_area1(self):
        poly_1 = draw_polygon.draw_polygon(self.ax1, self.fig)
        print(poly_1)
    
    def set_setpoint(self):
        self.setpoint = float(self.ent_setp.get())

    def set_pid_val(self):
        self.pid.Kp = float(self.ent_pidp.get())
        self.pid.Ki = float(self.ent_pidi.get())
        #print(self.pid.tunings)
    
    def pid_strt(self):
        self.set_setpoint()
        self.set_pid_val()
        
        while True:
            time.sleep(0.05)
            correction = self.pid((self.im_angl - self.setpoint + np.pi) % (2*np.pi) - np.pi)
            self.strvar_flat.set(correction)
            self.feedback()
            #print(self.pid.components)
            global stop_pid
            if stop_pid:
                break

    def enbl_pid(self):
        #setting up a listener for new im_phase
        global stop_pid
        stop_pid = False
        self.pid_thread = threading.Thread(target=self.pid_strt)
        self.pid_thread.daemon = True
        self.pid_thread.start()

    def pid_stop(self):
        global stop_pid
        stop_pid = True

    def on_close(self):
        plt.close(self.figr)
        plt.close(self.figp)
        if self.CAMERA:
            None
        else:
            self.spec_deactivate()
            avs.AVS_Done()
        self.win.destroy()
        self.parent.fbck_win = None