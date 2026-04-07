// #include <NimBLEDevice.h>
// #include <NimBLEAdvertisedDevice.h>
// Simple blink test for custom nRF52810 board
void setup()
{
    pinMode(19, OUTPUT);
    pinMode(20, OUTPUT);
}

void loop()
{
    digitalWrite(19, HIGH);
    digitalWrite(20, LOW);
    delay(500);

    digitalWrite(19, LOW);
    digitalWrite(20, HIGH);
    delay(500);
}