#!/usr/bin/env python

'''
http://blog.miguelgrinberg.com/post/easy-websockets-with-flask-and-gevent

'''

import serial
import re
import threading
import time
import Queue

from flask import Flask, request, redirect, url_for, send_from_directory
from flask.ext.socketio import SocketIO, emit

# app definition
app = Flask(__name__, static_url_path='')
app.config['SERVER_NAME'] = "localhost:8080"
socketio = SocketIO(app)

# cars
connected = False
port = '/dev/tty.usbmodem14211'
baud = 9600
ser = serial.Serial(port, 9600, timeout=0)
recv_data = ""

def handle_data(data):
    recv_data = data
    #print("recv_data: " + recv_data)
    m = re.match("^Raw: (\d+.\d+); - Voltage: (\d+.\d+); - Dust Density \[ug\/m3\]: (\d+.\d+);", recv_data)
    try:
        print m.group(1) + " " + m.group(2) + " " + m.group(3)
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
                #print("read: " + reading)
                handle_data(reading)
                time.sleep(1)
            except Exception as e:
                print("error, reconnecting: " + str(e))
                ser.close();
                time.seep(1)
                ser = serial.Serial(port, 9600, timeout=0)

@app.route('/<path:path>')
def static_proxy(path):
    return app.send_static_file("static/" + path)
    
@app.route('/')
def root():
    return app.send_static_file('static/index.html')
    
# @socketio.on('my event', namespace='/stream')
# def test_message(message):
#     print("sending: " + str(q.get()))
#     emit('my response', {'data': q.get()})
#
# @socketio.on('my broadcast event', namespace='/stream')
# def test_message(message):
#     emit('my response', {'data': message['data']}, broadcast=True)
#
@socketio.on('connect', namespace='/stream')
def test_connect():
    print('Cient connect')
    emit('my response', {'data': 'Connected'})
#
# @socketio.on('disconnect', namespace='/stream')
# def test_disconnect():
#     print('Client disconnected')

# send value changes
def broadcast_value(val):
    print("broadcasting: " + str(val))
    socketio.emit('my response', {'data': val}, namespace='/stream')
    print("sent")
    
if __name__ == "__main__":
    thread = threading.Thread(target=read_from_port, args=(ser,connected))
    thread.start()
    socketio.run(app)



    