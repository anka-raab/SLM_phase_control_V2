# SLM Phase Controller
A small GUI application for controlling the phase of the Santec SLM-300 (D-Lab).

To run the program, execute "controlPhaseSLM.py", it will load all the other files as it needs to.

Some settings (the wavelength used in the lab and the SLM type used) still need to be made on the code level before the program is run.
These can be found and changed in the file "settings.py".

## Structure

"avaspec_driver" contains drivers to communicate with the Aventes Spectrometer.

"background" contains the wavefront correction images for the SLMs provided by their manufacturer.

"gxipy" contains drivers to communicate with the Daheng camera.

"santec_driver" contains drivers to communicate with the Santec-SLMs.

"model" contains the scripts used for data calculation

"view" contains the scripts used for data and GUI displaying

## Documentation

A venir
