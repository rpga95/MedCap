
//////////
/////////  All Serial Handling Code,
/////////  It's Changeable with the 'outputType' variable
/////////  It's declared at start of code.
/////////

extern volatile int P;
extern volatile int minima;
extern volatile float coreTemp;
extern volatile float accel_x;
extern volatile float accel_y;
extern volatile float accel_z;

void serialOutput(){   // Decide How To Output Serial.
  switch(outputType){
    case PROCESSING_VISUALIZER:
      sendDataToSerial('S', Signal);     // goes to sendDataToSerial function
      break;
    case SERIAL_PLOTTER:  // open the Arduino Serial Plotter to visualize these data
      Serial.print(P);  //Blue
      Serial.print(",");
      Serial.print(minima);  //Red
      Serial.print(",");
      Serial.print(Signal);   //Green
      Serial.print(",");
      Serial.print(coreTemp);
      Serial.print(",");
      Serial.print(accel_x);  //Red
      Serial.print(",");
      Serial.print(accel_y);   //Green
      Serial.print(",");
      Serial.println(accel_z);
      
      break;
    default:
      break;
  }

}

//  Decides How To OutPut BPM and IBI Data
void serialOutputWhenBeatHappens(){
  switch(outputType){
    case PROCESSING_VISUALIZER:    // find it here https://github.com/WorldFamousElectronics/PulseSensor_Amped_Processing_Visualizer
      sendDataToSerial('B',BPM);   // send heart rate with a 'B' prefix
      sendDataToSerial('Q',IBI);   // send time between beats with a 'Q' prefix
      break;

    default:
      break;
  }
}

//  Sends Data to Pulse Sensor Processing App, Native Mac App, or Third-party Serial Readers.
void sendDataToSerial(char symbol, int data ){
    Serial.print(symbol);
    Serial.println(data);
  }
