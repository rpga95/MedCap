
/*  Pulse Sensor Amped 1.5    by Joel Murphy and Yury Gitman   http://www.pulsesensor.com

----------------------  Notes ----------------------  ----------------------
This code:
1) Blinks an LED to User's Live Heartbeat   PIN 13
2) Fades an LED to User's Live HeartBeat    PIN 5
3) Determines BPM
4) Prints All of the Above to Serial

Read Me:
https://github.com/WorldFamousElectronics/PulseSensor_Amped_Arduino/blob/master/README.md
 ----------------------       ----------------------  ----------------------
*/

#include <math.h>

//BT
#include <SimbleeBLE.h>


// Thermometer
#include <Wire.h> // I2C library, required for MLX90614
#include <C:\Users\raj19\Documents\Arduino\run_medcap\SparkFunMLX90614.h> // SparkFunMLX90614 Arduino library


// Accelerometer

#include <C:\Users\raj19\Documents\Arduino\run_medcap\SparkFunLIS3DH.h>
#include <SPI.h>


#define PROCESSING_VISUALIZER 1
#define SERIAL_PLOTTER  2

//  Variables
int pulsePin = 2;                 // Pulse Sensor purple wire connected to analog pin 0
int blinkPin = 13;                // pin to blink led at each beat
int fadePin = 5;                  // pin to do fancy classy fading blink at each beat
int fadeRate = 0;                 // used to fade LED on with PWM on fadePin

// Volatile Variables, used in the interrupt service routine!
volatile int BPM;                   // int that holds raw Analog in 0. updated every 2mS
volatile int Signal;                // holds the incoming raw data
volatile int IBI = 600;             // int that holds the time interval between beats! Must be seeded!
volatile boolean Pulse = false;     // "True" when User's live heartbeat is detected. "False" when not a "live beat".
volatile boolean QS = false;        // becomes true when Arduoino finds a beat.

extern volatile int maxima;
extern volatile int minima;

// SET THE SERIAL OUTPUT TYPE TO YOUR NEEDS
// PROCESSING_VISUALIZER works with Pulse Sensor Processing Visualizer
//      https://github.com/WorldFamousElectronics/PulseSensor_Amped_Processing_Visualizer
// SERIAL_PLOTTER outputs sensor data for viewing with the Arduino Serial Plotter
//      run the Serial Plotter at 115200 baud: Tools/Serial Plotter or Command+L
static int outputType = SERIAL_PLOTTER;


  // FIRST, CREATE VARIABLES TO PERFORM THE SAMPLE TIMING FUNCTION
  unsigned long lastTime;
  unsigned long thisTime;

//////THERMOMETER///////////////////////////////
IRTherm therm; // Create an IRTherm object to interact with throughout
const byte LED_PIN = 8; // Optional LED attached to pin 8 (active low)

volatile float coreTemp = 0;

//////THERMOMETER///////////////////////////////


//////ACCEL///////////////////////////////

LIS3DH myIMU; //Default constructor is I2C, addr 0x19.
volatile float accel_x = 0;
volatile float accel_y = 0;
volatile float accel_z = 0;
//////ACCEL///////////////////////////////

/////BT////////


  void setup(){
    override_uart_limit = true;
    pinMode(blinkPin,OUTPUT);         // pin that will blink to your heartbeat!
    pinMode(fadePin,OUTPUT);          // pin that will fade to your heartbeat!
    Serial.begin(115200);             // we agree to talk fast!
    // ADD THIS LINE IN PLACE OF THE interruptSetup() CALL
    lastTime = micros();              // get the time so we can create a software 'interrupt'
    // IF YOU ARE POWERING The Pulse Sensor AT VOLTAGE LESS THAN THE BOARD VOLTAGE,
    // UN-COMMENT THE NEXT LINE AND APPLY THAT VOLTAGE TO THE A-REF PIN
    //   analogReference(EXTERNAL);


    //////THERMOMETER///////////////////////////////
    
    //Serial.begin(9600); // Initialize Serial to log output
    therm.begin(); // Initialize thermal IR sensor
    therm.setUnit(TEMP_F); // Set the library's units to Farenheit
    // Alternatively, TEMP_F can be replaced with TEMP_C for Celsius or
    // TEMP_K for Kelvin.

    therm.setEmissivity(.98);

    pinMode(LED_PIN, OUTPUT); // LED pin as output
    setLED(LOW); // LED OFF

    //////THERMOMETER///////////////////////////////


    //////ACCEL///////////////////////////////
    //Serial.begin(9600);
    delay(1000); //relax...
    Serial.println("Processor came out of reset.\n");
  
    //Call .begin() to configure the IMU
    myIMU.begin();

    //////ACCEL///////////////////////////////


    ///////BT///////
    SimbleeBLE.deviceName = "MedCap";
    SimbleeBLE.advertisementData = "MedCapAd";
    SimbleeBLE.begin();

    
  } //end of setup()

  //IN THE LOOP, ADD THE CODE THAT WILL DO THE 2mS TIMING, AND CALL THE getPulse() routine.
  void loop(){

    serialOutput() ;

    thisTime = micros();            // GET THE CURRENT TIME
    if(thisTime - lastTime > 2000){ // CHECK TO SEE IF 2mS HAS PASSED
      lastTime = thisTime;          // KEEP TRACK FOR NEXT TIME
      getPulse();                   //CHANGE 'ISR(TIMER2_COMPA_vect)' TO 'getPulse()' IN THE INTERRUPTS TAB!
    }

  if (QS == true){     // A Heartbeat Was Found
                       // BPM and IBI have been Determined
                       // Quantified Self "QS" true when arduino finds a heartbeat
        fadeRate = 255;         // Makes the LED Fade Effect Happen
                                // Set 'fadeRate' Variable to 255 to fade LED with pulse
        serialOutputWhenBeatHappens();   // A Beat Happened, Output that to serial.
        QS = false;                      // reset the Quantified Self flag for next time
  }

  ledFadeToBeat();                      // Makes the LED Fade Effect Happen
  delay(20);                             //  take a break


//////THERMOMETER///////////////////////////////

  setLED(HIGH); //LED on
  
  // Call therm.read() to read object and ambient temperatures from the sensor.
  if (therm.read()) // On success, read() will return 1, on fail 0.
  {
    // Use the object() and ambient() functions to grab the object and ambient
  // temperatures.
  // They'll be floats, calculated out to the unit you set with setUnit().
    /*
    Serial.print("Object: ");
    Serial.println(therm.object());
    Serial.write('°'); // Degree Symbol
    Serial.println("F");
    Serial.print("Ambient: ");
    Serial.println(therm.ambient());
    Serial.write('°'); // Degree Symbol
    Serial.println("F");
    Serial.println();
    */
    coreTemp = therm.object();
  }
  setLED(LOW);

//////THERMOMETER///////////////////////////////


 //////ACCEL///////////////////////////////
  //Get all parameters
  /*
  Serial.print("\nAccelerometer:\n");
  Serial.print(" X = ");
  Serial.println(myIMU.readFloatAccelX(), 4);
  Serial.print(" Y = ");
  Serial.println(myIMU.readFloatAccelY(), 4);
  Serial.print(" Z = ");
  Serial.println(myIMU.readFloatAccelZ(), 4);
  
  delay(1000);
  */

  accel_x = myIMU.readFloatAccelX();
  accel_y = myIMU.readFloatAccelY();
  accel_z = myIMU.readFloatAccelZ();

 //////ACCEL///////////////////////////////



 //BT////////
  // If maxima > 512

  char buf[15];
   
  sprintf(buf, "%i,%i,%i,%i",round(maxima),round(coreTemp*10),100,101);
  SimbleeBLE.send(buf,sizeof(buf));

}



void ledFadeToBeat(){
    fadeRate -= 15;                         //  set LED fade value
    fadeRate = constrain(fadeRate,0,255);   //  keep LED fade value from going into negative numbers!
    analogWrite(fadePin,fadeRate);          //  fade LED
  }

void setLED(bool on)
{
  if (on)
    digitalWrite(LED_PIN, LOW);
  else
    digitalWrite(LED_PIN, HIGH);
}

/////////BT////////////


void SimbleeBLE_onReceive(char *data, int len){
  //Serial.println("Beginning"); 
  for(int i = 0; i < len; i++) {
    Serial.print(data[i]);
  }
  Serial.println();
  
}
void SimbleeBLE_onConnect() {
  SimbleeBLE.dualModeBegin();
}

void SimbleeBLE_onDisconnect() {
  SimbleeBLE.dualModeEnd();
}
