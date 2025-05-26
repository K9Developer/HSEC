#include <Arduino.h>
#include <SPI.h>
#include <Ethernet.h>

// SPI pins (match your wiring)
#define PIN_SPI_MISO  12
#define PIN_SPI_MOSI  11
#define PIN_SPI_SCLK  13
#define PIN_SPI_CS    14

// Optional: use a real MAC if needed
byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0x32, 0x01 };

void setup() {
  Serial.begin(115200);
  delay(4500);
  Serial.println("\n=== ESP32 + W5500 DHCP DEBUG START ===");

  // Step 1: Init SPI
  Serial.println("[DEBUG] Initializing SPI...");
  SPI.begin(PIN_SPI_SCLK, PIN_SPI_MISO, PIN_SPI_MOSI, PIN_SPI_CS);
  Ethernet.init(PIN_SPI_CS);  // required on ESP32

  // Step 2: Check SPI manually (optional low-level sanity)
  Serial.print("[DEBUG] SPI sanity (MISO): ");
  pinMode(PIN_SPI_MISO, INPUT_PULLUP);
  delay(10);
  Serial.println(digitalRead(PIN_SPI_MISO) ? "HIGH" : "LOW");

  // Step 3: Begin Ethernet with DHCP
  Serial.print("[DEBUG] Calling Ethernet.begin(mac)...\n");
  int dhcpResult = Ethernet.begin(mac);

  if (dhcpResult == 0) {
    Serial.println("[ERROR] DHCP failed ❌");

    EthernetHardwareStatus hwStatus = Ethernet.hardwareStatus();
    EthernetLinkStatus linkStatus = Ethernet.linkStatus();

    Serial.print("[DEBUG] Hardware status: ");
    switch (hwStatus) {
      case EthernetNoHardware: Serial.println("No hardware detected"); break;
      case EthernetW5100:       Serial.println("W5100 detected"); break;
      case EthernetW5200:       Serial.println("W5200 detected"); break;
      case EthernetW5500:       Serial.println("W5500 detected ✅"); break;
      default:                  Serial.println("Unknown"); break;
    }

    Serial.print("[DEBUG] Link status: ");
    switch (linkStatus) {
      case Unknown:  Serial.println("Unknown"); break;
      case LinkON:   Serial.println("Link is ON ✅"); break;
      case LinkOFF:  Serial.println("Link is OFF ❌"); break;
    }

    Serial.println("[DEBUG] Your W5500 is likely not initialized or not wired correctly.");
    Serial.println("[DEBUG] Check: power, SPI pinout, pullups, reset, and CS logic.");
    while (true) delay(1000);
  }

  // Step 4: DHCP success
  Serial.println("[SUCCESS] Got IP via DHCP 🎉");
  Serial.print("IP Address : "); Serial.println(Ethernet.localIP());
  Serial.print("Subnet Mask: "); Serial.println(Ethernet.subnetMask());
  Serial.print("Gateway IP : "); Serial.println(Ethernet.gatewayIP());
  Serial.print("DNS Server : "); Serial.println(Ethernet.dnsServerIP());
}

void loop() {
  // Nothing in loop — just polling for now
  delay(1000);
}
