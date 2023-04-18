# -*- coding: utf-8 -*-
"""
Created on Tue Apr 11 17:49:30 2023

@author: atto
"""

from matplotlib import *
import sys
import pylab as plt
from PIL import Image, ImageTk
import numpy as np


im = Image.open("C:/data/2023-04-11/2023-04-11-2.bmp")
p = np.array(im)

plt.figure()
plt.imshow(np.log10(p))