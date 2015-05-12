#!/usr/bin/env python

'''
Reads values from a file or serial port, then uses websocket to update the HTML client graph in real-time

Examples:

# a log file with 3 numbers separated by space
./server.py  -F -o console.log -r '^([0-9]+) ([0-9]+) ([0-9]+)'

# a serial port with 3 numbers extracted from a sentence
./server.py -o /dev/tty.usbmodem1421 -w 1 -r '^Raw: (\d+.\d+); - Voltage: (\d+.\d+); - Dust Density \[ug\/m3\]: (\d+.\d+);' -n raw,volt,dust

# another simple serial monitor a single value
./server.py -o /dev/tty.usbmodem1421 -w 1 -r '^([0-9]+)' -n 'biebers served',somevar -p 8081

'''

import sys
import os
import serial
import re
import threading
import time
import datetime
import collections
import json
from flask import Flask, request, redirect, url_for, send_from_directory, render_template
from flask.ext.socketio import SocketIO, emit
from optparse import OptionParser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger("server")
app = Flask(__name__, static_url_path='')
socketio = SocketIO(app)

# defaults
default_port = '/dev/tty.usbmodem'
default_baud = 9600
default_regex = '^Raw: (\d+.\d+); - Voltage: (\d+.\d+); - Dust Density \[ug\/m3\]: (\d+.\d+);'
# other regex examples: '^([0-9]+) ([0-9]+) ([0-9]+)'

# internals
connected = False
values = collections.deque(maxlen=500)
realtime = True


class FileHandler(FileSystemEventHandler):
  '''
  the handler for file change events when monitoring a file ( directory )
  '''
  def on_modified(self, event):
      logger.debug("file change event received")
      read_file(options.file, options.buffer_size)
      

def read_from_port(serial_port, connected=False):
  '''
  function which will forever read a serial port, and sleep a little to allow bytes to stack up on the port.
  this is not ideal, but since there is no bytesAvailable() method, this needs to be like this for now.

  call handle_data when its got some bytes to pass on.
  
  this should run in its own thread
  '''
  while not connected:
    connected = True
    while True:
      try:
        reading = serial_port.readline().decode()
        handle_data(reading)
        time.sleep(options.wait)
      except Exception as e:
        print("error, reconnecting: " + str(e))
        serial_port.close();
        time.seep(1)
        serial_port = serial.Serial(port, 9600, timeout=0)


def handle_data(data):
  '''
  called by read_from_port / read_from_file, matches data groups via the regex, calls broadcase_values with a list of values[float,int,...]
  '''
  recv_data = data
  logger.debug("handling data: " + recv_data)
  m = re.match(options.regex, recv_data)
  
  try:
    # extract the number of groupings from the regex
    num_groups = len(m.groups())
    logger.debug("groups: " + str(num_groups))
    
    # results holder
    results = []
    
    # start with a date in the results as 1st argument
    results.append(datetime.datetime.now().strftime('%a %b %d %y %H:%M:%S %Z%z'))
    
    # loop over groups and make a list of the findings
    x = 1;
    while x <= num_groups:
      logger.debug("group: " + str(x))
      logger.debug("group contents " + str(m.group(x)))
      results.append(m.group(x))
      x=x+1
    
    # save results in values ( for browser refresh )
    values.append(results)
    
    # broadcast results
    logger.debug("broadcasting: " + str(results))
    broadcast_value(results)
    
  except Exception as e:
    logger.debug("exception processing data " + str(e))
    time.sleep(0.1)


def monitor_file(filename, bufsize):
  '''
  monitors a directory for file changes, unfortunately we cannot monitor the file specifically,
  therefore, make sure your log files are in their own directory.
  '''
  event_handler = FileHandler()
  observer = Observer()
  observer.schedule(event_handler, path=os.path.dirname(os.path.realpath(filename)), recursive=False)

  observer.start()
  try:
      while True:
          time.sleep(options.wait)
  except KeyboardInterrupt:
      observer.stop()
  observer.join()
  

def read_file(filename, bufsize):
  '''
  seeks the end-of-file less the bufsize, then grabs the last bunch of lines and passes
  the very last one to handle_data.
  '''
  f = open(filename)
  f.seek(os.stat(filename).st_size-bufsize)
  lines = f.readlines()
  f.close()
  logger.debug("lines: " + str(lines))
  logger.debug("sending last element: " + lines[-1])
  handle_data(lines[-1])


# serve index.html
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
  logger.info('client connect')
  emit('connect accept', {'data': 'Connected'})


# socket.io refresh request
@socketio.on('chart config', namespace='/stream')
def refresh(message):
  try:
    logger.info('client requests chart config')
    # subtract 1 ( the time index ) from number of values
    emit('chart config', {'data': {'number': len(values.pop())-1, 'titles': options.names} })
    
  except Exception, e:
    time.sleep(2)
    logger.warn("error sending chart config, sending reconnect instruction " + str(e))
    emit("chart config error", {'data': 'unable to determine number of charts'})


# socket.io refresh request
@socketio.on('refresh', namespace='/stream')
def refresh(message):
  logger.info('client requesting refresh')
  # shutdown the realtime events to prevent timeline contamination
  realtime = False
  for v in list(values):
    emit('chart refresh data', {'data': v})
  logger.info("client refresh complete, enabling realtime events and sending completed message")
  realtime = True
  emit('chart refresh complete', {'data': 'done!'})


# send a value change from outside the Flask context.
def broadcast_value(val):
  if realtime:
    socketio.emit("chart data", {'data': val}, namespace='/stream')
  else:
    logger.warning("realtime event suspended");


# list builder for optparse, takes a comma deliminated string, converts to list
def list_callback(option, opt, value, parser):
  setattr(parser.values, option.dest, value.split(','))


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
                    default=True,
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
                    default=64,
                    type="int",
                    help="buffer size")
  
  parser.add_option("-r", "--regex", 
                    dest="regex", 
                    default=default_regex,
                    help="regex which extracts groups of values you want to send to html client")
  
  parser.add_option("-n", "--names", 
                    dest="names",
                    type='string',
                    default="",
                    action='callback',
                    callback=list_callback,
                    help="comma separated names for the values in regex groups e.g. volts,particles,mass")                  
                    
  parser.add_option("-w", "--wait", 
                    dest="wait", 
                    default=0.1,
                    type="int",
                    help="seconds to wait between polling handling data ( FILE / SERIAL )") 

  # parse the args
  (options, args) = parser.parse_args()
  
  # set the neccesary
  app.config['SERVER_NAME'] = "%s:%s" % (options.hostname, options.port)
  
  if options.serial_mode:
    serial_port = serial.Serial(options.file, options.baud, timeout=0)
    thread = threading.Thread(target=read_from_port, args=(serial_port,connected))
  else:
    thread = threading.Thread(target=monitor_file, args=(options.file, options.buffer_size))

  thread.start()
  time.sleep(1)
  socketio.run(app, host=options.hostname)



    