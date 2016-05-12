#!/usr/bin/env python

#######################################################################
#####-eyetracking.py-###################### John Mumford, 2013 ########
#######################################################################
#######################################################################

## This is an interface for the Mirametrix eye tracker unit
## The unit has two infrared cameras and a built-in tcp server over a serial connection
## The unit's built-in server waits to receive XML statements
## that contain eye tracking parameters before it starts to send eye data
## It then transmits XML statements at ~60hz which could be written to a file
## or otherwise manipulated. this script allows someone to start and stop
## the eyetracking unit by calling start_eyetracking() and stop_eyetracking()
## from within their own python code, by using the line "import eyetracking.py"
## usually their code would be displaying images on the screen
## for which they want viewer's eye position to be tracked
## in a psychology research setting


## Provided by module##################################################
__all__ = ['start_eyetracking','stop_eyetracking']

## Required by module: ################################################
"""
socket, required for the TCP connection
unicodedata, required to convert server unicode data into python-friendly strings
threading, required so module can run independently of script from which it is called
xml.etree.ElementTree allows XML statements to be addressed as dictionaries
os and sys required to check if output file path already exists / to create it
"""
import socket
import unicodedata
import threading
import time
import xml.etree.ElementTree as xmlObject
import os, sys

## Environment Variables: #############################################
"""
server is a string representing IP address of windows server running mirametrix software
port is an integer
verbose is boolean
"""
SERVER = '172.21.104.49'
PORT = 4242
VERBOSE = False

"""
python_version is initialzed as an integer when the module is imported. 
Represents python version (i.e. 2, 3) since some functions require
different methods depending on version
"""
PYTHON_VERSION = int(sys.version[0])
if PYTHON_VERSION != 2:
	print('Warning: python interpreter not version 2.x')





#######################################################################
#### HELPER FUNCTIONS #################################################
#######################################################################
#######################################################################

#######################################################################
### connect ###########################################################
"""
PRE: eyetracking server waiting on same network as this client 
  e.g. server  responds to ping, not firewalled

POST: attempts to connect to
  server using socket module.
  Prints 'connected!', or an error message, and returns boolean 'True'
"""

#sock refers to the socket connection, defined by the socket module
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def connect():
	try:			
		sock.connect((SERVER, PORT))
		print('connected!')
		return True
	except: 
		print("whoops! couldn't connect to " + SERVER + " on port " + str(PORT) +'.')

def disconnect():
	global sock
	sock.close()
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


#######################################################################
#### tx (transmit) ####################################################
"""
PRE: an open socket connection to server i.e. connect() returns True

POST: encodes 'msg' from a python-compatible string into the unicode data
 required by the server. 
 
 Sends using socket's buit-in send fn which handles the transport.
"""

def tx(msg):
	sock.send(str.encode(msg + '\r\n'))


#######################################################################
### rx (receive) ######################################################
"""
PRE: an open socket connection to server i.e. connect() returns True

POST: Decodes a string of bytes representing unicode data
 from the eyetracking server. 
 
 'size' is an integer
 representing the number of bytes per line
 
this function formats the unicode data into a python-friendly
 string before presenting it as the output. 
 
 Uses different syntax
 depending on python environment version.
"""

def rx():
	size=4096
	if PYTHON_VERSION == 3:
		rx = (sock.recv(size))
		string = bytes.decode(rx)
		string = string.replace('\r','')
		return string    
	if PYTHON_VERSION == 2:
		rx = str.decode(sock.recv(size))
		string = unicodedata.normalize('NFKD', rx).encode('ascii','ignore')
		string = string.replace('\r','')
		return string   


	
#######################################################################
### initialize_server #################################################

"""uses tx helper function to transmit xml commands to the 
server, to enable eye data transmission

acknowledgements should be received by the server as xml
"""
def initialize_server():
	tx('<SET ID="ENABLE_SEND_DATA" STATE="1" />')
	tx('<SET ID="ENABLE_SEND_COUNTER" STATE="1" />')
	tx('<SET ID="ENABLE_SEND_EYE_LEFT" STATE="1" />')
	tx('<SET ID="ENABLE_SEND_EYE_RIGHT" STATE="1" />')
	tx('<SET ID="ENABLE_SEND_POG_LEFT" STATE="1" />')
	tx('<SET ID="ENABLE_SEND_POG_RIGHT" STATE="1" />')
	tx('<SET ID="ENABLE_SEND_POG_BEST" STATE="1" />')
	tx('<SET ID="ENABLE_SEND_PUPIL_LEFT" STATE="1" />')
	tx('<SET ID="ENABLE_SEND_PUPIL_RIGHT" STATE="1" />')
	tx('<SET ID="ENABLE_SEND_POG_FIX" STATE="1" />')
	tx('<SET ID="ENABLE_SEND_TIME" STATE="1" />')

	
	print('server is sending data!')
	
	

#######################################################################
#### fill_buffer ######################################################
"""
A function that consumes the list 'line_overflow', and a string from the server 
(retreived using the rx() function). The strings contain one or more lines 
of XML statements. 

fill_buffer produces a list, by
separating the input string at each newline character. 

The buffer handles the problem caused as a result of 
the TCP packets having a fixed no. of bytes, and length of the XML statements 
being variable. It uses the global 'line_overflow' variable to store the 
incomplete XML statements that can otherwise be found at the end of 
a 'line_list'. 

Once called, the function fill_buffer() gathers strings from the server until 
a string that ends in a '>' is found, so one function call appends multiple 
values to "line_buffer".
"""
#line_overflow is an empty global list for storing incomplete XML statements
line_overflow = []
def fill_buffer():
	line_buffer = []
	global line_overflow
	partial_XML = rx()
	line_list = partial_XML.splitlines()
	iteration = 0
	if VERBOSE:
		##tx('<GET ID="TIME_TICK_FREQUENCY" />')
		print('buffering    ')
		print('iteration:' + str(iteration) + ', line_list:', line_list)
	if len(line_overflow) > 0:
		line_list[0] = line_overflow[0] + line_list[0]
		line_overflow = []
		if VERBOSE:
			print ('buffer concatenated to lineList[0]:', line_list[0])
	for line in line_list:
		if line[-1] == '>':
			line_buffer = line_buffer + [line]
			if VERBOSE:
				print ('added '+str(line)+' to line_buffer')
		else: 
			line_overflow = [line]
			if VERBOSE:
				print ('!!! ' + str(line) + ' has replaced line_overflow')
	return line_buffer
    
    
    
#######################################################################
#### parse_XML ########################################################
"""
A helper function that consumes nothing but reads the output list from 
previous function fill_buffer. The list items are XML statements and
xmlObject, imported by this module, addresses individual elements of each
XML statement. 

This is where every line of XML received from the server is interpreted, 
and the data values written to output, if relevant (i.e. tag == "REC")

"""

calibrated = False
keys_received = False
def parse_XML():
	global calibrated
	global keys_received
	
	for XML in fill_buffer() :
		#write this line of XML to XML output file
		XML_output.write(XML)
		XML_output.write("\n")
		
		#initialize variables for working with XML, 
		#imported above as xmlObject
		thisXML = xmlObject.fromstring(XML)
		tag = (thisXML.tag)
		dict = (thisXML.attrib)
		keys = (thisXML.keys())
		values = dict.values()
		
		#optional prints information if verbose 
		if VERBOSE:	
			print "XML:", XML
			print "dict:", dict
			print "keys:", keys
			print "calibrated?", calibrated
			print "tag:", tag
			
		
		#set global 'calibrated' to True once calibration is complete
		if "ID" in keys:
			if dict['ID'] == "CALIB_RESULT":
				tx('<SET ID="CALIBRATE_SHOW" STATE="0" />')
				calibrated = True
				
				
				
		#write to calibration output file
		if tag == "CAL":
			for key in keys:
				calibration_output.write(key + ",")
			calibration_output.write("\n")
			for value in values:
				calibration_output.write(value + ",")
			calibration_output.write("\n")
			calibration_output.flush()
			
		
		#write to record output file
		if calibrated == True:
			if tag == "REC":
				if not keys_received:
					for key in keys:
						record_output.write(key+",")
						keys_received = True
					record_output.write("\n")
				for value in values:
					record_output.write(value+",")
				record_output.write("\n")
				record_output.flush()
		
		
		
		
		
		
#######################################################################
#### perform_calibration() ############################################
"""
uses the Mirametrix server software to calibrate by sending the 
calibrate_show then calibrate_start commands. The calibration screen
will be displayed on the primary monitor of the windows server in full screen
at the current screen resolution.
"""

def perform_calibration():
	global calibrated
	tx('<SET ID="CALIBRATE_SHOW" STATE="1"  />')
	tx('<SET ID="CALIBRATE_START" STATE="1" />')
		

	

    
#######################################################################
#### THREADING CLASS ##################################################
#######################################################################
#######################################################################

""" 
Using threading allows the interface functions below
to be called from another file, without interrupting the execution
of the other file.

A variable, "is_running", is shared by the thread and the file from
which it is started. The thread will continue to execute the callback function
until "is_running" is set to False. Both the thread and the file from which
it is started need to obtain a "lock"  before reading or mutating "is_running" 
so that they are not both accessing the variable at the same time. The threading
module imported at the top of this file handles this.
"""

class WorkerThread(threading.Thread):	
	def __init__(self, callback):
		super(WorkerThread, self).__init__()
		self.callback = callback
		self.lock = threading.Lock()
		
	def stop_running(self):
		self.lock.acquire()
		self.is_running = False
		self.lock.release()
		
		
	def run(self):
		if VERBOSE:
			print("Collection thread started")
		self.is_running = True
		while True:
			XML_callback()
			self.lock.acquire()
			if not self.is_running:
				if VERBOSE:
					print("Done thread")
				self.lock.release()
				break
			else:
				self.lock.release()
			#	
			
def XML_callback():
	parse_XML()
	

tracker = WorkerThread(XML_callback)


#######################################################################
#### INTERFACE ########################################################
#######################################################################
#######################################################################

"""
start_eyetracking(): consumes a string representing the output filename
and calls the helper functions in order to initialize the connection and 
start the thread
"""
def start_eyetracking(output_filename=False):
	
	## if file name not passed as parameter, takes raw input
	if output_filename == False:
		output_filename = raw_input("Enter the output file name: ") 
	
	## the opened output files in 'write' mode:
	global record_output
	record_output = open(output_filename+"_record.csv", 'w')
	global calibration_output
	calibration_output = open(output_filename + "_calibration.csv", 'w')
	global XML_output
	XML_output = open(output_filename + "_xml.csv", 'w')
	
	if connect():
		initialize_server()
		tracker.start()
		perform_calibration()
		

def stop_eyetracking():
	global calibrated
	calibrated = False
	global tracker
	tracker.stop_running()
	tracker = WorkerThread(XML_callback)
	disconnect()
	global record_output
	record_output.close()
	global calibration_output
	calibration_output.close()
	global XML_output
	calibration_output.close()
	print("Finished the eyetracking thread")
	


