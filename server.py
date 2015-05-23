#!/usr/bin/env python

'''


Reads date from a file / serial port / stdin / tcp socket, then uses regex's to extract plotable valyes, and serves the values over 
websocket to update the HTML client graph in real-time.

Examples:

# a log file with 3 numbers separated by space
./server.py  -F -o console.log -r '^([0-9]+) ([0-9]+) ([0-9]+)'

# a serial port with 3 numbers extracted from a sentence
./server.py -o /dev/tty.usbmodem1421 -w 1 -r '^Raw: (\d+.\d+); - Voltage: (\d+.\d+); - Dust Density \[ug\/m3\]: (\d+.\d+);' -n raw,volt,dust

# another simple serial monitor a single value
./server.py -o /dev/tty.usbmodem1421 -w 1 -r '^([0-9]+)' -n 'biebers served',somevar -p 8081

# listen on a tcp socket for some events separated by newline
./server.py --ss --sp=8082  -r '^([0-9]+)' -n 'u/g dust cm3'

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
import fileinput
import ast
from random import randint
from flask import Flask, request, redirect, url_for, send_from_directory, render_template
from flask.ext.socketio import SocketIO, emit
import SocketServer
from optparse import OptionParser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')
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
values = collections.deque(maxlen=10080)
realtime = True
running = True

CHART_DATA="chart data"
CONNECT_ACCEPT="connect accept"
CHART_CONFIG="chart config"
CHART_CONFIG_ERROR="chart config error"
CHART_MARKER="chart marker"
CHART_REFRESH_DATA="chart refresh data"
CHART_REFRESH_COMPLETE="chart refresh complete"


class FileHandler(FileSystemEventHandler):
  '''
  the handler for file change events when monitoring a file ( directory )
  '''
  def on_modified(self, event):
      logger.debug("file change event received")
      read_file(options.file, options.buffer_size)


class SocketHandler(SocketServer.StreamRequestHandler):
  def handle(self):
    # self.rfile is a file-like object created by the handler;
    # we can now use e.g. readline() instead of raw recv() calls
    self.data = self.rfile.readline().strip()
    logger.info(self.data)
    handle_data(CHART_DATA, self.data)
    # Likewise, self.wfile is a file-like object used to write back
    # to the client
    #self.wfile.write(self.data.upper())
  

def socket_server():
  logger.info("starting tcp socket server on %s" % options.socket_server_port )
  sserver = SocketServer.TCPServer(('', options.socket_server_port), SocketHandler)
  while running:
    sserver.handle_request()
  logger.info("socket_server harrikiri")
  sserver.shutdown()
  sys.exit()


def read_from_port(serial_port, connected=False):
  '''
  function which will forever read a serial port, and sleep a little to allow bytes to stack up on the port.
  this is not ideal, but since there is no bytesAvailable() method, this needs to be like this for now.

  call handle_data when its got some bytes to pass on.
  
  this should run in its own thread
  '''
  while not connected:
    connected = True
    while running:
      try:
        reading = serial_port.readline().decode()
        handle_data(CHART_DATA, reading)
        time.sleep(options.wait)
      except Exception as e:
        print("error, reconnecting: " + str(e))
        serial_port.close();
        time.seep(1)
        serial_port = serial.Serial(port, 9600, timeout=0)
    logger.info("read_from_port shutting down")
    sys.exit()


def handle_data(topic, data):
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
    
    results.append(topic)
    
    # Date.UTC(year,month,day,hours,minutes,seconds,millisec)
    tn = datetime.datetime.now()
    # ms = int(tn.strftime('%f'))/1000
    results.append(tn.strftime('%Y, %m, %d, %H, %M, %S, %f')[:-3])
   
    # results.append(tn.strftime('%Y, %m, %d, %H, %M, %S'))
    
    # loop over groups and make a list of the findings
    x = 1;
    while x <= num_groups:
      logger.debug("group: " + str(x))
      logger.debug("group contents " + str(m.group(x)))
      results.append(m.group(x))
      x=x+1
    
    # save results in values ( for browser refresh )
    values.append(results)
    
    # write to file
    logger.debug("writing to file " + str(datafile))
    datafile.write(str(results) + '\n')
    
    # broadcast results
    logger.debug("broadcasting: " + str(results))
    broadcast_value(results)
    
  except Exception as e:
    logger.debug("exception processing data " + str(e))
    time.sleep(1)


def monitor_stdin():
  while running:
    try:
      data = sys.stdin.readline()
      handle_data(CHART_DATA, data)
    except Exception as e:
      logger.warning("exception processing stdin " + str(e))
      time.sleep(options.wait)
  logger.info("monitor_stdin going down")
  sys.exit()
  

def testmode():
  while running:
    try:
      data = str(randint(1,100)) + ' ' + str(randint(1,100)) + ' ' + str(randint(1,100))
      handle_data(CHART_DATA, data)
      # time.sleep(randint(1,3)*0.1)
      time.sleep(5)
    except Exception as e:
      logger.warning("exception processing testmode " + str(e))
      time.sleep(options.wait)
  logger.info("testmode going down")
  sys.exit()


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
      while running:
          time.sleep(options.wait)
  except KeyboardInterrupt:
      observer.stop()
  observer.join()
  logger.info("monitor_file shutting down")
  sys.exit()
  

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
  handle_data(CHART_DATA, lines[-1])


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
  emit(CONNECT_ACCEPT, {'data': 'Connected'})


# socket.io refresh request
@socketio.on('chart config', namespace='/stream')
def refresh(message):
  try:
    logger.info('client requests chart config: ' + str(message))
    logger.info('data values len: ' + str(len(values.pop())-2))
    # subtract 1 ( the time index ) from number of values
    emit(CHART_CONFIG, {'data': {'number': len(values.pop())-2, 'titles': options.names} })
    
  except Exception, e:
    time.sleep(2)
    logger.warn("error sending chart config, sending reconnect instruction " + str(e))
    emit(CHART_CONFIG_ERROR, {'data': str(e)})


# plot point of interrest
@socketio.on('flag', namespace='/stream')
def flag(message):
  logger.info("client requesting flag plot: " + str(message))
  try:
    results = [] 
    results.append(CHART_MARKER)
    results.append(message['data'])
    values.append(results)
    logger.debug("appended to values: " + str(results))
    datafile.write(str(results) + '\n')
    logger.debug("written to file")
  except Exception, e:
    logger.warn("unable to append the data file: " + str(e));
  logger.info("broadcasting: " + message['data'])
  socketio.emit(CHART_MARKER, {'data': message['data']}, namespace='/stream')


# socket.io refresh request
@socketio.on('refresh', namespace='/stream')
def refresh(message):
  logger.info('client requesting refresh: ' + str(message))
  # shutdown the realtime events to prevent timeline contamination
  realtime = False
  i = 0;
  
  e_max = message['data']
  e = e_max

  if e>len(values):
    e=len(values)
    logger.debug("setting max history available to %s" % e)
  
  while e>=1:
    d = values[-1*e]
    logger.debug("refresh data before emit: " + str(d[0]) + " data: " + str(d[1:len(d)]))
    
    if (d[0] == CHART_DATA):
      emit(CHART_REFRESH_DATA, {'data': d[1:len(d)]})
    else:
      logger.info("Emitting to: " + str(d[0]) + " data: " + str(d[1:len(d)]))
      emit(d[0], {'data': d[1:len(d)]})
    i=i+1
    e=e-1
  
  # for v in list(values):
  #   logger.debug("emitting value: " + str(v))
  #   if (v[0] == CHART_DATA):
  #     emit(CHART_REFRESH_DATA, {'data': v[1:len(v)]})
  #   else:
  #     logger.info("Emitting to: " + str(v[0]) + " data: " + str(v[1:len(v)]))
  #     emit(v[0], {'data': v[1:len(v)]})
  #   i=i+1
  logger.info("client refresh complete, enabling realtime events and sending completed message, samples: " + str(i))
  time.sleep(2)
  realtime = True
  emit(CHART_REFRESH_COMPLETE, {'data': 'done!'})


# send a value change from outside the Flask context.
def broadcast_value(val):
  if realtime:
    logger.info("broadcasting")
    socketio.emit(CHART_DATA, {'data': val[1:len(val)]}, namespace='/stream')
  else:
    logger.warning("realtime events suspended");


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
                    default="8081",
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
                    help="regex which extracts groups of values you want to send to html client e.g. '^([0-9]+) ([0-9]+) ([0-9]+)'")
  
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
                    
  parser.add_option("-t", "--test", 
                    dest="test_mode", 
                    default=False,
                    action="store_true",
                    help="test mode data")
                    
  parser.add_option("-d", "--datafile", 
                    dest="datafile", 
                    default="data.dat",
                    help="history data file")
  
  parser.add_option("-x", 
                    dest="nohistory",
                    default=False,
                    action="store_true",
                    help="dont import history")

  parser.add_option("--ss", 
                    dest="socket_server",
                    default=False,
                    action="store_true",
                    help="socket server")

  parser.add_option("--sp", 
                    dest="socket_server_port",
                    default=8082,
                    type="int",
                    help="socket server port")


  # parse the args
  (options, args) = parser.parse_args()
  
  # set the neccesary
  app.config['SERVER_NAME'] = "%s:%s" % (options.hostname, options.port)
  
  
  if not options.nohistory:
    for line in fileinput.input(options.datafile):
        try:
          # simple check for newline at end of line
          if line[-1] == "\n":
            logger.debug("read data: " + line)
            values.append(ast.literal_eval(line))
            # values.append(line)
          else:
            logger.error("crc: bad line: " + line)
        except Exception, e:
          logger.error("exception: bad line: " + str(e))
          pass
  datafile = open(options.datafile, "a")
  
  
  if options.socket_server:
    logger.info("starting socket server")
    sserver = SocketServer.TCPServer(('', options.socket_server_port), SocketHandler)
    thread = threading.Thread(target=sserver.serve_forever)
    #thread = threading.Thread(target=socket_server)
    thread.daemon = True
  elif options.test_mode:
    logger.info("Test Mode")
    thread = threading.Thread(target=testmode)
    thread.daemon = True
  elif options.serial_mode:
    serial_port = serial.Serial(options.file, options.baud, timeout=0)
    thread = threading.Thread(target=read_from_port, args=(serial_port,connected))
  elif options.file != '-':
    thread = threading.Thread(target=monitor_file, args=(options.file, options.buffer_size))
  elif options.file == '-':
    logger.info("monitoring stdin")
    thread = threading.Thread(target=monitor_stdin)
  else:
    logger.warn("unable to deal with input")
  
  thread.start()
  time.sleep(1)
  
  try:
    logger.info("starting socketio")
    socketio.run(app, host=options.hostname)
    logger.info("socketio done")
  except KeyboardInterrupt:
    pass
  except Exception, e:
    logger.warn("error starting socketio: %s" % e)
  
  running = False
  logger.info("shutting down")
  datafile.close()
  logger.info("files closed")
  
