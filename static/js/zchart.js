// My ZChart Class

var ZChart = function(name, dl, intervalType, valueFormatString)
{
  this.name = name;
  this.dataLength = dl;
  this.dps = [];
  this.yVal = 0;
  this.xVal = 0;
  this.self = this;
  this.intervalType = intervalType;
  this.valueFormatString = valueFormatString;
  this.eventRate = 1; // default event rate, will recalc on update
  this.eventTokens = 0; // used to keep track of value changes. 
  this.eventRateCounter = 0; // counter for how many times we have checked
  
  
  // create a new DIV
  var ni = document.getElementById('charts');
  var newdiv = document.createElement('div');
  var divIdName = 'zchartContainer' + chartCount;
  newdiv.setAttribute('id', divIdName);
  newdiv.setAttribute('class', 'z-depth-1');
  newdiv.style.height = '200px';
  newdiv.style.width = '100%';
  newdiv.innerHTML = '';
  ni.appendChild(newdiv);
  
  // divider
  var divider = document.createElement('div');
  divider.setAttribute('class', 'divider');
  ni.appendChild(divider);
  
  this.chart = new CanvasJS.Chart("zchartContainer" + chartCount,
  {
    // animationEnabled: true,
    // exportEnabled: true,
    // exportFileName: this.name,
    interactivityEnabled: false,
		title :{
			text: this.name
		},
    axisX: {
      valueFormatString: this.valueFormatString,
      intervalType: this.intervalType,
    },
		data: [{
			type: "area",
      xValueType: "dateTime",
      color: "rgba(40,175,101,0.6)",
      markerSize: 0,
			dataPoints: this.dps 
		}]
	});
  
  
  this.update = function(x1, y1)
  {
    // console.log("updating x1: " + x1 + " and y1: " + y1);
    if (this.dataLength != dataLength )
    {
      console.log("dataLength changed, updating");
      this.dataLength = dataLength;
    }
    
    this.yVal=Math.round(y1);
    // this.xVal=x1;
    
    var xVal=x1.split(", ").map(function(x){return parseInt(x)});
    // console.log(this.xVal[0], this.xVal[1], this.xVal[2], this.xVal[3], this.xVal[4], this.xVal[5], this.xVal[6]);
    
    // console.log(new Date (Date.UTC(xVal[0], xVal[1], xVal[2], xVal[3], xVal[4], xVal[5], xVal[6])));
    
  	this.dps.push({
  		y: this.yVal,
      // x: new Date(x1)
      // x: new Date(x1).setUTCMilliseconds(new Date().getMilliseconds())
      // x: new Date(this.xVal[0], this.xVal[1], this.xVal[2], this.xVal[3], this.xVal[4], this.xVal[5], this.xVal[6]).setUTCMilliseconds(new Date().getMilliseconds())
      
      // with millis
      x: new Date(Date.UTC(xVal[0], xVal[1], xVal[2], xVal[3], xVal[4], xVal[5], xVal[6]))
      // without milliss
      // x: new Date(Date.UTC(this.xVal[0], this.xVal[1], this.xVal[2], this.xVal[3], this.xVal[4], this.xVal[5]))

      // x: Date(this.xVal[0], this.xVal[1], this.xVal[2], this.xVal[3], this.xVal[4], this.xVal[5])

  	});

    if (this.dps.length > (this.dataLength*this.eventRate))
    {
      this.dps.shift();
    }
    
    this.eventTokens++;
    
  }


  this.clear = function()
  {
    // this.eventRateCounter=0;
    // this.eventTokens=0;
    while (this.dps.length > 0)
    {   
      this.dps.shift();
    }
  }


  this.zrender = function()
  {
    // console.log("rendering " + self.dps.length + " dl " + self.dataLength * self.eventRate);
    while (self.dps.length > (self.dataLength*self.eventRate))
    {
          self.dps.shift();
    }
    self.chart.render();
  }
  
  this.calculate_event_rate = function()
  {
    // set the eventRate equal to the eventTokens
    self.eventRateCounter++;
    self.eventRate = Math.ceil(self.eventTokens / self.eventRateCounter);
    
    // if the rate is insane, probably did a history load, reset for resample
    if (self.eventRate >= 16)
    {
      self.eventTokens=0;
    }
    
    // self.eventTokens=0;
    console.log("eventRate: " + self.eventRate + " dataLength: " + (self.dataLength*self.eventRate) );
  }


  var self = this;
  window.setInterval(this.zrender, refresh_rate);
  window.setInterval(this.calculate_event_rate, 1000);
  chartCount++;
    
}