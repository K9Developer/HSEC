
// Camera Data
#define CAMERA_NAME "HSEC_CAM_2233"
#define MAX_FPS     60

// Board Data
#define SERIAL_BAUD_RATE 115200

// Network Data
#define MESSAGE_SIZE_BYTE_LENGTH 4

// Ethernet Pins / Data
#define PIN__ETH_SPI_MISO   12   // Master-In / Slave-Out
#define PIN__ETH_SPI_MOSI   11   // Master-Out / Slave-In
#define PIN__ETH_SPI_SCLK   13   // SPI clock
#define PIN__ETH_SPI_CS     14   // Chip-select (nSS)
#define PIN__ETH_IRQ        10   // W5500 INT (active-low)
#define PIN__ETH_RESET       9   // W5500 RESET (active-low)
#define ETH_PHY_ADDR         1
#define SPI3_HOST            2

// Camera Pins
#define PIN__CAM_ENABLE     8
#define PWDN_GPIO_NUM  -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  3
#define SIOD_GPIO_NUM  48
#define SIOC_GPIO_NUM  47
#define Y9_GPIO_NUM    18
#define Y8_GPIO_NUM    15
#define Y7_GPIO_NUM    38
#define Y6_GPIO_NUM    40
#define Y5_GPIO_NUM    42
#define Y4_GPIO_NUM    46
#define Y3_GPIO_NUM    45
#define Y2_GPIO_NUM    41
#define VSYNC_GPIO_NUM 1
#define HREF_GPIO_NUM  2
#define PCLK_GPIO_NUM  39