#!/usr/bin/env python

'''
Reads values from a arduino on a serial port, then uses websocket to update the HTML client graphs.
'''

import sys
import os
import serial
import re
import threading
import time
import collections

from flask import Flask, request, redirect, url_for, send_from_directory, render_template
from flask.ext.socketio import SocketIO, emit
from optparse import OptionParser

# app definition
app = Flask(__name__, static_url_path='')
socketio = SocketIO(app)



# vars
connected = False
default_port = '/dev/tty.usbmodem621'
default_baud = 9600
default_regex = '^Raw: (\d+.\d+); - Voltage: (\d+.\d+); - Dust Density \[ug\/m3\]: (\d+.\d+);'


# save some history for client refreshes
values = collections.deque(maxlen=500)


def handle_data(data):
  '''
  called by read_from_port
  '''
  recv_data = data
  m = re.match(options.regex, recv_data)
  try:
    print m.group(1) + " " + m.group(2) + " " + m.group(3)
    values.append([m.group(1), m.group(2), m.group(3)])
    
    # broadcast all three values as a list
    broadcast_value([m.group(1), m.group(2), m.group(3)])
    
  except Exception as e:
    pass
    time.sleep(0.1)


def read_from_port(serial_port, connected=False):
  '''
  function which will forever read a serial port, and sleep a little to allow bytes to stack up on the port.
  this is not ideal, but since there is no bytesAvailable() method, this needs to be like this for now. 

  call handle_data when its got some bytes to pass on.
  '''
  while not connected:
    connected = True
    while True:
      try:
        reading = serial_port.readline().decode()
        handle_data(reading)
        time.sleep(1)
      except Exception as e:
        print("error, reconnecting: " + str(e))
        serial_port.close();
        time.seep(1)
        serial_port = serial.Serial(port, 9600, timeout=0)


def read_from_file(filename, bufsize):
  fiter = 0
  fsize = os.stat(filename).st_size
  lines = 1
  
  with open(filename) as f:
      if bufsize > fsize:
          bufsize = fsize-1
      data = []
      while True:
          fiter +=1
          f.seek(fsize-bufsize*fsize)
          data.extend(f.readlines())
          if len(data) >= lines or f.tell() == 0:
              handle_data(''.join(data[-lines:]))
              break



# route / to index
@app.route('/')
def index():
  return app.send_static_file('index.html')

# serve the static content
@app.route('/<path:path>')
def static_proxy(path):
  return app.send_static_file("static/" + path)

# socket.io connect event
@socketio.on('connect', namespace='/stream')
def connect():
  print('Cient connect')
  emit('connect-accept', {'data': 'Connected'})

# socket.io refresh request
@socketio.on('refresh', namespace='/stream')
def refresh(message):
  print('Client refresh requested')

  # send the history
  for v in list(values):
    emit('chart data', {'data': v})

# send a value change from outside the Flask context.
def broadcast_value(val):
  socketio.emit("chart data", {'data': val}, namespace='/stream')

if __name__ == "__main__":
  parser = OptionParser()
  parser.add_option("-H", "--host", 
                    dest="hostname", 
                    default="localhost",
                    help="http service hostname / address to listen on")
                    
  parser.add_option("-p", "--port", 
                    dest="port", 
                    default="8080",
                    help="http service port to listen on")
                    
  parser.add_option("-S", 
                    dest="serial_mode", 
                    action="store_true",
                    help="serial mode")
                    
  parser.add_option("-F", 
                    dest="serial_mode",
                    action="store_false",
                    help="file mode")
                    
  parser.add_option("-o", "--open", 
                    dest="file", 
                    default=default_port,
                    help="file or serial port to monitor")
                    
  parser.add_option("-b", "--baud", 
                    dest="baud", 
                    default=default_baud,
                    help="serial port baud rate")
                    
  parser.add_option("-B", "--buffer", 
                    dest="buffer_size", 
                    default=8192,
                    help="buffer size")
  
  parser.add_option("-r", "--regex", 
                    dest="regex", 
                    default=default_regex,
                    help="regex which extracts groups of values you want to send to html client")
  

  (options, args) = parser.parse_args()
  
  # set the neccesary
  app.config['SERVER_NAME'] = "localhost:%s" % options.port
  
  if options.serial_mode:
    serial_port = serial.Serial(options.file, options.baud, timeout=0)
    thread = threading.Thread(target=read_from_port, args=(serial_port,connected))
  else:
    thread = threading.Thread(target=read_from_file, args=(options.file, options.buffer_size))
    
  thread.start()
  socketio.run(app)



    