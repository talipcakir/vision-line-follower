// 5 Kanal IR Sensör Pinleri (Digital)
const int sensor1 = 2;   // En sol
const int sensor2 = 3;
const int sensor3 = 4;   // Orta
const int sensor4 = 7;
const int sensor5 = 12;  // En sag

void setup() {
  Serial.begin(9600);

  pinMode(sensor1, INPUT);
  pinMode(sensor2, INPUT);
  pinMode(sensor3, INPUT);
  pinMode(sensor4, INPUT);
  pinMode(sensor5, INPUT);

  Serial.println("=== 5 KANAL SENSOR KALIBRASYON ===");
  Serial.println("Sensoru beyaz ve siyah yuzey uzerinde gezdirin.");
  Serial.println("0 = Siyah, 1 = Beyaz (veya tersi)");
  Serial.println();
}

void loop() {
  int s1 = digitalRead(sensor1);
  int s2 = digitalRead(sensor2);
  int s3 = digitalRead(sensor3);
  int s4 = digitalRead(sensor4);
  int s5 = digitalRead(sensor5);

  Serial.print("S1:");
  Serial.print(s1);
  Serial.print("\tS2:");
  Serial.print(s2);
  Serial.print("\tS3:");
  Serial.print(s3);
  Serial.print("\tS4:");
  Serial.print(s4);
  Serial.print("\tS5:");
  Serial.println(s5);

  delay(1000);
}
