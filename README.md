# eyetracking
This is an interface for the Mirametrix eye tracker unit 
The unit has two infrared cameras and a built-in tcp server over a serial connection 
The unit's built-in server waits to receive XML statements 
that contain eye tracking parameters before it starts to send eye data 
It then transmits XML statements at ~60hz which could be written to a file 
or otherwise manipulated. this script allows someone to start and stop 
the eyetracking unit by calling start_eyetracking() and stop_eyetracking() 
from within their own python code, by using the line "import eyetracking.py" 
usually their code would be displaying images on the screen 
for which they want viewer's eye position to be tracked 
in a psychology research setting
