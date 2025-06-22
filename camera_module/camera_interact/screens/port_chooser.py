import serial_manager as serial_manager
from textual.app import ComposeResult
from textual.widgets import Static, Button, ListView, ListItem
from textual.screen import Screen

class PortChooserScreen(Screen):
    def __init__(self, on_port_selected=None):
        super().__init__()
        self.on_port_selected = on_port_selected
        self.lv = None

    def compose(self) -> ComposeResult:
        ports = serial_manager.SerialManager.get_serial_ports()
        self.ports = ports
        yield Static("Select the camera port:", id="prompt")
        self.lv = ListView(*[ListItem(Static(f"{p.name} - {p.description}")) for p in ports], id="port-list")
        yield self.lv
        yield Button("Refresh", id="refresh")
        
    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        try:
            if self.ports and self.on_port_selected:
                self.app.call_later(lambda: self.on_port_selected(self.ports[0]))
        except Exception as e:
            print(f"Error in port selection: {e}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            ports = serial_manager.SerialManager.get_serial_ports()
            self.ports = ports
            lv = self.query_one("#port-list", ListView)
            lv.clear()
            for p in ports:
                lv.append(ListItem(Static(f"{p.name} - {p.description}")))