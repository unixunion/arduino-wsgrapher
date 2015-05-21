# arduino-wsgrapher

A simple http server that serves a HTML client that can graph in realtime values from your arduino.

## overview

* can monitor a file / serial port / stdin / tcp socket
* regex extraction of values
* dynamically configurable HTML client

## client

The HTML5 client uses CanvsJS for graphs and socket.io for websocket connections. The client uses websockets to obtain graph configurations, and plot values. Graphs are created dynamically during the websocket handshake process. The number of charts created is equal to the number of value groups being extracted with the regex.

The client operates as follows:

* the HTML client is downloaded via HTTP GET
* jquery, socket.io and canvas.js are included
* ws connect to server
* ws request graph config ( number of graphs, titles )
* ws request data history graphs
* ws onmessage plot values for all graphs

## server

The server is a python flask + socketio application. It spawns a worker thread which can monitor a serial port or a file, and handles data from it. Values are then extracted from the data using regex groups, each group being a integer value which will become a graph.


![Screenshot](https://raw.githubusercontent.com/unixunion/arduino-wsgrapher/master/screenshot.png)
![Screenshot2](https://raw.githubusercontent.com/unixunion/arduino-wsgrapher/master/screenshot2.png)

## UI
http://materializecss.com/grid.html
