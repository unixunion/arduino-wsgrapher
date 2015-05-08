var ZChart = function(name, dataLength)
{
  this.name = name;
  this.dataLength = dataLength;
  this.dps = [];
  this.yVal = 0;
  this.xVal = 0;
  
  // create a new DIV
  console.log("creating div element for " + chartCount);
  var ni = document.getElementById('charts');
  var newdiv = document.createElement('div');
  var divIdName = 'zchartContainer' + chartCount;
  newdiv.setAttribute('id', divIdName);
  newdiv.style.height = '200px';
  newdiv.style.width = '100%';
  newdiv.innerHTML = '';
  ni.appendChild(newdiv);
  
  this.chart = new CanvasJS.Chart("zchartContainer" + chartCount,
  {
		title :{
			text: this.name
		},	
		data: [{
			type: "splineArea",
			dataPoints: this.dps 
		}]
	});
  
  
  this.update = function(y1)
  {
    this.yVal=Math.round(y1)
  	this.dps.push({
  		y: this.yVal,
  		x: this.xVal
  	});
    
    // move time along
    this.xVal++;
    
  	if (this.dps.length > this.dataLength)
  	{
  		this.dps.shift();
  	}
    
  }

  window.setInterval(this.chart.render, refresh_rate);
  
  chartCount++;
    
}