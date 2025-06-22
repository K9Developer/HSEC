from textual.app import App
from screens.port_chooser import PortChooserScreen
from screens.serial_monitor import SerialMonitorScreen

class CameraInteractApp(App):
    CSS_PATH = None

    async def handle_port_selected(self, port):
        await self.push_screen(SerialMonitorScreen(port))

    def on_mount(self) -> None:
        self.push_screen(PortChooserScreen(on_port_selected=self.handle_port_selected))

def main():
    CameraInteractApp().run()

if __name__ == "__main__":
    main()