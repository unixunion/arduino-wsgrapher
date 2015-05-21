# arduino-wsgrapher

A simple http server that serves a HTML client that can graph in realtime values from your arduino.

## overview

* can monitor multiple source types
	* file
	* serial port
	* stdin
	* tcp socket 	
* grouped regex extraction of values
	* '^([0-9]+) ([0-9]+) ([0-9]+)'
	* '^Raw: (\d+.\d+); - Voltage: (\d+.\d+); - Dust Density \[ug\/m3\]: (\d+.\d+);' 
* dynamically HTML client



## server

The server is a python flask + socketio application. It spawns a worker thread which monitors the input and handles data from it. Values are then extracted from the data using regex groups, each group being a integer value which will become a graph.


![Screenshot](https://raw.githubusercontent.com/unixunion/arduino-wsgrapher/master/screenshot.png)
![Screenshot2](https://raw.githubusercontent.com/unixunion/arduino-wsgrapher/master/screenshot2.png)

### options

```
Usage: server.py [options]

Options:
  -h, --help            show this help message and exit
  -H HOSTNAME, --host=HOSTNAME
                        http service hostname / address to listen on
  -p PORT, --port=PORT  http service port to listen on
  -S                    serial mode
  -F                    file mode
  -o FILE, --open=FILE  file or serial port to monitor
  -b BAUD, --baud=BAUD  serial port baud rate
  -B BUFFER_SIZE, --buffer=BUFFER_SIZE
                        buffer size
  -r REGEX, --regex=REGEX
                        regex which extracts groups of values you want to send
                        to html client e.g. '^([0-9]+) ([0-9]+) ([0-9]+)'
  -n NAMES, --names=NAMES
                        comma separated names for the values in regex groups
                        e.g. volts,particles,mass
  -w WAIT, --wait=WAIT  seconds to wait between polling handling data ( FILE /
                        SERIAL )
  -t, --test            test mode data
  -d DATAFILE, --datafile=DATAFILE
                        history data file
  -x                    dont import history
  --ss                  socket server
  --sp=SOCKET_SERVER_PORT
                        socket server port
```


### serial port

Monitor a serial port which is emiting numbers every 1 second

```
./server.py -o /dev/tty.usbmodem1421 -w 1 -r '^([0-9]+)' -n 'biebers served' -p 8081
```

### file
Monitor a file which has 3 numbers written to it. Remember to put the log in its own directory, since python watchdog watches for changes on a directory level.

```
./server.py  -F -o console.log -r '^([0-9]+) ([0-9]+) ([0-9]+)'
```

## stdin

Monitor some process's stdout

```
somecommand | ./server.py -o - -F -r '^([0-9]+) ([0-9]+) ([0-9]+)'
```

## tcp socket

Opens a tcp socket where data can be sent, each newline trigers handle data.

```
./server.py --ss --sp=8082  -r '^([0-9]+)' -n 'u/g dust cm3'
```

## client

The HTML5 client uses CanvsJS for graphs and socket.io for websocket connections. The client uses websockets to obtain graph configurations, and plot values. Graphs are created dynamically during the websocket handshake process. The number of charts created is equal to the number of value groups being extracted with the regex.

The client operates as follows:

* the HTML client is downloaded via HTTP GET
* jquery, socket.io and canvas.js are included
* ws connect to server
* ws request graph config ( number of graphs, titles )
* ws request data history graphs
* ws onmessage plot values for all graphs

## UI
http://materializecss.com/grid.html
