// #include <Arduino.h>
// #include <NimBLEDevice.h>

// #define DEVICE_NAME "ASL_Glove"
// #define SERVICE_UUID        "7e2a2b10-5b9a-4c8f-9d6a-2f6f2a4f8b01"
// #define CHARACTERISTIC_UUID "7e2a2b11-5b9a-4c8f-9d6a-2f6f2a4f8b01"

// struct __attribute__((packed)) imu_debug_frame
// {
//     uint32_t t_ms;
//     uint8_t imu_ok;
//     uint8_t chip_id;
//     uint16_t status;
//     int16_t acc_x;
//     int16_t acc_y;
//     int16_t acc_z;
//     int16_t gyr_x;
//     int16_t gyr_y;
//     int16_t gyr_z;
// };

// static imu_debug_frame frame = {};
// static NimBLECharacteristic *frameCharacteristic = nullptr;
// static volatile bool bleClientConnected = false;

// class ServerCallbacks : public NimBLEServerCallbacks
// {
//     void onConnect(NimBLEServer *pServer, NimBLEConnInfo &connInfo) override
//     {
//         bleClientConnected = true;
//     }

//     void onDisconnect(NimBLEServer *pServer, NimBLEConnInfo &connInfo, int reason) override
//     {
//         bleClientConnected = false;
//         NimBLEDevice::startAdvertising();
//     }
// };

// static ServerCallbacks serverCallbacks;

// static void initBle(void)
// {
//     NimBLEDevice::init(DEVICE_NAME);

//     NimBLEServer *server = NimBLEDevice::createServer();
//     server->setCallbacks(&serverCallbacks);

//     NimBLEService *service = server->createService(SERVICE_UUID);

//     frameCharacteristic = service->createCharacteristic(
//         CHARACTERISTIC_UUID,
//         NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
//     );

//     frameCharacteristic->setValue((const uint8_t *)&frame, sizeof(frame));

//     server->start();

//     NimBLEAdvertising *advertising = NimBLEDevice::getAdvertising();
//     advertising->setName(DEVICE_NAME);
//     advertising->addServiceUUID(SERVICE_UUID);
//     advertising->enableScanResponse(true);
//     advertising->start();
// }

// void setup(void)
// {
//     delay(200);

//     frame.t_ms = 0;
//     frame.imu_ok = 1;
//     frame.chip_id = 0x43;
//     frame.status = 0x1234;
//     frame.acc_x = 100;
//     frame.acc_y = 200;
//     frame.acc_z = 300;
//     frame.gyr_x = 400;
//     frame.gyr_y = 500;
//     frame.gyr_z = 600;

//     initBle();
// }

// void loop(void)
// {
//     frame.t_ms = millis();
//     frameCharacteristic->setValue((const uint8_t *)&frame, sizeof(frame));

//     if (bleClientConnected)
//     {
//         frameCharacteristic->notify();
//     }

//     delay(100);
// }

