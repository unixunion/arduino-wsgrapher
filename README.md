# arduino-wsgrapher

A simple http server that serves a websocket client, and monitors a arduino's output values in order to push values to the web browser and ultimately update some graphs.

## Server

The server is a python flash + socketio application. It spawns a worker thread which monitors a serial port, and handles data from the serial port in a somewhat rudimentary way. 

When a regex match is successful, the data is pushed to the HTML clients via a socketio.emit call.

## HTML Client

The graphing is done via canvasjs, and the client utilizes socket.io and jquery. The client is downloaded from the flask application, and immediately creates a websocket connection. After the connection is established, it does a "refresh" request which tell the server to push the last 500 datapoints.




![Screenshot](https://raw.githubusercontent.com/unixunion/arduino-wsgrapher/master/screenshot.gif)