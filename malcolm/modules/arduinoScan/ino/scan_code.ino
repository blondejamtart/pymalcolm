#include <AFMotor.h>
#include <Servo.h>


// Number of steps per output rotation
// Change this as per your motor's specification
const int stepsPerRevolution = 48;

int range = 0;  	// linear stage range of travel (steps)
int LO_LIM = 2; 	// digital pin for low limit
int HI_LIM = 13; 	// digital pin for hi limit
int dir = 1;  		// direction of travel
int margin = 4;   	// set soft limit this many steps short of hard limit
int r = 0;
int x = 0;
int r_vel_mult = 20;
int TRIG = 9;


// connect motor to port #1 (M1 and M2)
AF_Stepper linear(stepsPerRevolution, 1);
Servo rotation;

void do_home() {
  range = 0;
  Serial.println("HOME_START");
  rotation.write(90);
  int lo = digitalRead(LO_LIM);
  int hi = digitalRead(HI_LIM);
  while (lo && hi) {  
    linear.step(1, BACKWARD, INTERLEAVE);
    lo = digitalRead(LO_LIM);
    hi = digitalRead(HI_LIM);
  }
  if (!lo) {
    dir = -1;
  }
  range += 20;  
  linear.step(20, FORWARD, INTERLEAVE);
  lo = digitalRead(LO_LIM);
  hi = digitalRead(HI_LIM); 
  while (lo && hi) {
    range += 1;  
    linear.step(1, FORWARD, INTERLEAVE);
    lo = digitalRead(LO_LIM);
    hi = digitalRead(HI_LIM); 
  }
  if (dir == -1) {
    int tmp = LO_LIM;
    LO_LIM = HI_LIM;
    HI_LIM = tmp;
  }
  // range = 2*range;
  x = 0;
  r = 0;
  linear.step(range/2, BACKWARD, INTERLEAVE);
  Serial.println("HOME_END");
}

void setup() {
  pinMode(LO_LIM, INPUT);
  pinMode(HI_LIM, INPUT);
  pinMode(TRIG, OUTPUT);
  Serial.begin(9600);
  Serial.println("Stepper test!");
  rotation.attach(10);  
  linear.setSpeed(100);
  //do_home();
  //delay(1000);
}

void report_status() {
  int lo = digitalRead(LO_LIM);
  int hi = digitalRead(HI_LIM);   
  Serial.print("posn:x=");
  Serial.print(String(x));
  Serial.print("/");
  Serial.print(String(range));
  Serial.print(",r=");
  Serial.print(String(r));
  Serial.print(";lims:hi=");  
  Serial.print(String(!hi));
  Serial.print(",lo=");
  Serial.print(String(!lo));
  Serial.print("\n");  
}

void scan_x_fast() {
  Serial.println("scan with x as fast!");
  int r_step = 0;
  rotation.write(90);
  linear.step(range/2 - margin, BACKWARD, INTERLEAVE);
  while (r_step < 20) {
    linear.step(range - margin, FORWARD, INTERLEAVE);
    rotation.write(110);
    delay(20);
    rotation.write(90);
    r_step++;
    linear.step(range - margin, BACKWARD, INTERLEAVE);
    rotation.write(110);
    delay(20);
    rotation.write(90);
    r_step++; 
  }  
  linear.step(range/2 - margin, FORWARD, INTERLEAVE);
}

void scan_r_fast(double r_vel, int r_steps, int x_start, int x_inc, int x_end, int time_step) {
  int errCode = (abs(x_start) > range / 2) + 2 * (abs(x_end) > range / 2)  + 4* ((x_end - x_start) % x_inc != 0);
  if (errCode > 0)
  {
    Serial.print("SCAN_ERR:");
    Serial.print(String(errCode));
    Serial.print("\n");
    return;
  }  
  if (x_start < 0)
    linear.step(abs(x_start), BACKWARD, INTERLEAVE);
  else
    linear.step(x_start, FORWARD, INTERLEAVE);
  x = x_start;
  report_status();
  
  Serial.println("SCAN_READY");
  // Wait for run request
  int start = 0;
  while (!start) {
    if (Serial.available() > 0) {
      // read the incoming byte:
      String request = Serial.readStringUntil('\n');
      start = (request == "run");
    }
    delay(10);
  }  
  Serial.println("SCAN_START");
  
  int trigs = 0;
  int snake = 0;
  while (x < x_end) {    
    trigs = 0;
    if (snake % 2 == 0) {    
      rotation.write(90+(r_vel*r_vel_mult));
      while (trigs < r_steps) {
        trigs++;
        digitalWrite(TRIG, HIGH);
        delay(time_step);
        r += r_vel_mult;     
        digitalWrite(TRIG, LOW);
        delay(time_step);
      }
    } else {         
      rotation.write(90-(r_vel*r_vel_mult));
      while (trigs < r_steps) {
        trigs++;
        digitalWrite(TRIG, HIGH);
        delay(time_step);
        r -= r_vel_mult; 
        digitalWrite(TRIG, LOW);        
        delay(time_step);
      }       
    }
    snake++;
    rotation.write(90); 
    linear.step(x_inc, FORWARD, INTERLEAVE);
    x+=x_inc;
    if (Serial.available() > 0) {
      // read the incoming byte:
      String request = Serial.readStringUntil('\n');
      if (request == "abort") {
        if (x < 0)
          linear.step(abs(x), FORWARD, INTERLEAVE);
        else
          linear.step(x, BACKWARD, INTERLEAVE);
        Serial.println("SCAN_ABRT");
        return;
      }
    }
    report_status();    
  }
  
  if (x_end < 0)
    linear.step(abs(x_end), FORWARD, INTERLEAVE);
  else
    linear.step(x_end, BACKWARD, INTERLEAVE);
  x -= x_end;
  report_status();
  Serial.println("SCAN_END");
}

void loop() {  
  if (Serial.available() > 0) {
    // read the incoming byte:
    String request = Serial.readStringUntil('\n');
    if (request == "home") {
      do_home();
    } else if (request == "?") {
      report_status();
    } else if (request[0] == 'x') {
      int pos = request.substring(2).toInt();
      if (request[1] == ':')
        pos = pos - x; 
      if (pos < 0)
        linear.step(abs(pos), BACKWARD, INTERLEAVE);
      else
        linear.step(pos, FORWARD, INTERLEAVE);
      x += pos;
      
    } else if (request[0] == 'r') {
      
    } else {
      int args_start = request.indexOf('(');
      // scan(r:vel,step;x:start,inc,stop;time_step)
      if (args_start != -1 && request.substring(0, args_start) == "scan") {      
        int args_end = request.indexOf(')');
        String args = request.substring(args_start+1, args_end);
        args.replace(" ", "");
        String first = args.substring(0, args.indexOf(';'));
        String temp = args.substring(args.indexOf(';') + 1);
        String second = temp.substring(0, temp.indexOf(';'));
        String t_step = temp.substring(temp.indexOf(';')+1);
        
        if (first[0] == 'r') {
          double r_vel = first.substring(first.indexOf(':')+1, first.indexOf(',')).toFloat();
          int r_steps = first.substring(first.indexOf(',')+1).toInt();
          int x_start = second.substring(second.indexOf(':')+1, second.indexOf(',')).toInt();
          String tmp = second.substring(second.indexOf(',')+1);
          int x_inc = tmp.substring(0, tmp.indexOf(',')).toInt();
          int x_end = tmp.substring(tmp.indexOf(',')+1).toInt();
          scan_r_fast(r_vel, r_steps, x_start, x_inc, x_end, t_step.toInt());
        } else if (first[0] == 'x') {
          //scan_x_fast();
        }
      } else {
        Serial.println(request.substring(0, args_start-1));   
      }
    }
  }   
}
