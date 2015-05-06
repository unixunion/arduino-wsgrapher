#!/usr/bin/env python

'''
Reads values from a arduino on a serial port, then uses websocket to update the HTML client graphs.
'''

import serial
import re
import threading
import time
import collections

from flask import Flask, request, redirect, url_for, send_from_directory, render_template
from flask.ext.socketio import SocketIO, emit

# app definition
app = Flask(__name__, static_url_path='')
app.config['SERVER_NAME'] = "localhost:8080"
socketio = SocketIO(app)

# vars
connected = False
port = '/dev/tty.usbmodem14211'
baud = 9600
ser = serial.Serial(port, baud, timeout=0)

# save some history for client refreshes
values = collections.deque(maxlen=500)

def handle_data(data):
    recv_data = data
    m = re.match("^Raw: (\d+.\d+); - Voltage: (\d+.\d+); - Dust Density \[ug\/m3\]: (\d+.\d+);", recv_data)
    try:
        print m.group(1) + " " + m.group(2) + " " + m.group(3)
        values.append(m.group(3))
        broadcast_value(m.group(3))
    except Exception as e:
        pass
        time.sleep(0.1)
    
def read_from_port(ser, connected=False):
  while not connected:
    connected = True
    while True:
      try:
        reading = ser.readline().decode()
        handle_data(reading)
        time.sleep(1)
      except Exception as e:
        print("error, reconnecting: " + str(e))
        ser.close();
        time.seep(1)
        ser = serial.Serial(port, 9600, timeout=0)

# route / to index
@app.route('/')
def index():
    return app.send_static_file('index.html')

# serve the static content
@app.route('/<path:path>')
def static_proxy(path):
    return app.send_static_file("static/" + path)

@socketio.on('connect', namespace='/stream')
def connect():
    print('Cient connect')
    # send the history
    emit('my response', {'data': 'Connected'})
    
@socketio.on('refresh', namespace='/stream')
def refresh(message):
    print('Client refresh requested')

    # send the history
    for v in list(values):
      print("emitting")
      emit('my response', {'data': v})
      

# send value changes
def broadcast_value(val):
    socketio.emit('my response', {'data': val}, namespace='/stream')
    
if __name__ == "__main__":
    thread = threading.Thread(target=read_from_port, args=(ser,connected))
    thread.start()
    socketio.run(app)



    