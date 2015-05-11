// My ZChart Class

var ZChart = function(name, dl)
{
  this.name = name;
  this.dataLength = dl;
  this.dps = [];
  this.yVal = 0;
  this.xVal = 0;
  this.self = this;
  
  // create a new DIV
  // console.log("creating div element for " + chartCount);
  var ni = document.getElementById('charts');
  var newdiv = document.createElement('div');
  var divIdName = 'zchartContainer' + chartCount;
  newdiv.setAttribute('id', divIdName);
  newdiv.setAttribute('class', 'z-depth-1');
  newdiv.style.height = '200px';
  newdiv.style.width = '100%';
  newdiv.innerHTML = '';
  ni.appendChild(newdiv);
  
  var divider = document.createElement('div');
  divider.setAttribute('class', 'divider');
  ni.appendChild(divider);
  
  this.chart = new CanvasJS.Chart("zchartContainer" + chartCount,
  {
    interactivityEnabled: false,
		title :{
			text: this.name
		},
		data: [{
			type: "area",
      color: "rgba(40,175,101,0.6)",
      markerSize: 0,
			dataPoints: this.dps 
		}]
	});
  
  
  this.update = function(x1, y1)
  {
    //console.log("updating x1: " + x1 + " and y1: " + y1);
    if (this.dataLength != dataLength )
    {
      console.log("dataLength changed, updating");
      this.dataLength = dataLength;
    }
    
    this.yVal=Math.round(y1);
    this.xVal=x1;
  	this.dps.push({
  		y: this.yVal,
  		x: new Date(x1)
  	});

  	if (this.dps.length > this.dataLength)
  	{
		  this.dps.shift();
  	}
    
  }

  this.clear = function()
  {
    while (this.dps.length > 0)
    {   
      this.dps.shift();
    }
  }


  this.zrender = function()
  {
  	while (self.dps.length > self.dataLength)
  	{
		  self.dps.shift();
  	}
    self.chart.render();
  }

  var self = this;
  window.setInterval(this.zrender, refresh_rate);
  
  chartCount++;
    
}