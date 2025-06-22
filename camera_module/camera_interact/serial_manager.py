import serial.tools.list_ports

class Port:
    def __init__(self, name: str, serial: str, description: str):
        self.name = name
        self.description = description
        self.serial = serial

    def __repr__(self):
        return f"Port(name={self.name}, description={self.description}, serial={self.serial})"

class SerialManager:

    @staticmethod
    def get_serial_ports() -> list[Port]:
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(Port(name=port.device, description=port.description, serial=port.serial_number))
        return ports
    
if __name__ == "__main__":
    ports = SerialManager.get_serial_ports()
    print("Available Serial Ports:")
    for port in ports:
        print(port)