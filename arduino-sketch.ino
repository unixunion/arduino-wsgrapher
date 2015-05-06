//#include <SPI.h>
//#include <Wire.h>
//#include <U8glib.h>

/*
 Standalone Sketch to use with a Arduino Fio and a
 Sharp Optical Dust Sensor GP2Y1010AU0F

 Blog: http://arduinodev.woofex.net/2012/12/01/standalone-sharp-dust-sensor/
 Code: https://github.com/Trefex/arduino-airquality/

 For Pin connections, please check the Blog or the github project page
 Authors: Cyrille Médard de Chardon (serialC), Christophe Trefois (Trefex)
 Changelog:
   2012-Dec-01:  Cleaned up code

 This work is licensed under the
 Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
 To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
 or send a letter to Creative Commons, 444 Castro Street, Suite 900,
 Mountain View, California, 94041, USA.
*/

// OLED Display
//#define OLED_MOSI  1
//#define OLED_CLK   2
//#define OLED_DC    4
//#define OLED_CS    3
//#define OLED_RESET 5

//U8GLIB_SSD1306_ADAFRUIT_128X64 display(OLED_CLK, OLED_MOSI, OLED_CS, OLED_DC, OLED_RESET);

int measurePin = 6;
int ledPower = 12;

int samplingTime = 280;
int deltaTime = 40;
int sleepTime = 9680;

float voMeasured=0.0;
float calcVoltage=0.0;
float dustDensity=0.0;

void setup() {
  Serial.begin(9600);
  Wire.begin();
  pinMode(ledPower, OUTPUT);
  delay(3000);
}

void loop() {
//  display.drawStr( 0, 20, "Hello World!");

  digitalWrite(ledPower, LOW); // power on the LED
  delayMicroseconds(samplingTime);

  voMeasured = analogRead(measurePin); // read the dust value

  delayMicroseconds(deltaTime);
  digitalWrite(ledPower, HIGH); // turn the LED off
  delayMicroseconds(sleepTime);

  // 0 - 3.3V mapped to 0 - 1023 integer values
  // recover voltage
  calcVoltage = voMeasured * (5.0 / 1024);

  // linear eqaution taken from http://www.howmuchsnow.com/arduino/airquality/
  // Chris Nafis (c) 2012
//  dustDensity = (0.17 * calcVoltage - 0.1) * 1000;
  dustDensity = (0.17 * calcVoltage) * 1000;

  Serial.print("Raw: ");
  Serial.print(voMeasured);

  Serial.print("; - Voltage: ");
  Serial.print(calcVoltage);

  Serial.print("; - Dust Density [ug/m3]: ");
  Serial.print(dustDensity);
  Serial.println(";");

  delay(1000);


}

// fuck this
float sumUp(float * n, int samples) {
  float res = 0.0;
  int i;
  for (i = -1; i <= samples; i++) {
    res+=n[i];
    n[i] = 0.0;
  }
  
  float r = res / samples;
  return r;
}