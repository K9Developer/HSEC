import time
import threading
import serial
import logging
from datetime import datetime

from textual.app import ComposeResult
from textual.widgets import Static, Button, Label, RichLog, Input, Footer
from textual.screen import Screen
from textual.containers import Container, VerticalScroll
from textual.reactive import reactive
from textual.binding import Binding

logging.basicConfig(
    filename="log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("SerialMonitor")


class BaudRateModal(Screen):
    """Simple modal dialog to enter a new baud rate."""

    DEFAULT_CSS = """
    BaudRateModal {
        align: center middle;
    }
    
    #modal {
        padding: 1 2;
        width: 60;
        height: 11;
        border: thick $primary;
        background: $surface;
    }
    
    #modal-title {
        width: 100%;
        text-align: center;
        padding-bottom: 1;
    }
    
    #input-container {
        width: 100%;
        height: 3;
        margin-bottom: 1;
    }
    
    #baud-rate-input {
        width: 100%;
    }
    
    #button-container {
        width: 100%;
        height: 3;
        align: right middle;
    }
    
    Button {
        margin-left: 1;
    }
    """

    def __init__(self, current_baud_rate: int = 115200) -> None:
        super().__init__()
        self.current_baud_rate = current_baud_rate

    def compose(self) -> ComposeResult:
        with Container(id="modal"):
            yield Label("Enter New Baud Rate", id="modal-title")
            with Container(id="input-container"):
                yield Input(value=str(self.current_baud_rate), id="baud-rate-input")
            with Container(id="button-container"):
                yield Button("Cancel", variant="primary", id="cancel-button")
                yield Button("Apply", variant="success", id="apply-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "apply-button":
            try:
                baud = int(self.query_one("#baud-rate-input", Input).value)
                self.dismiss(baud)
            except ValueError:
                self.dismiss(None)


class SerialMonitorScreen(Screen):
    BINDINGS = [
        Binding("ctrl+b", "change_baud_rate", "Change Baud Rate"),
        Binding("ctrl+q", "go_back", "Go Back"),
    ]

    DEFAULT_CSS = """
    #header {
        width: 100%;
        height: 3;
        background: $accent;
        color: $text;
        padding: 0 1;
    }
    
    #port-info {
        width: 70%;
    }
    
    #status {
        width: 30%;
        text-align: right;
    }
    
    #serial-output {
        width: 100%;
        height: 1fr;
        background: $surface;
        color: $text;
        overflow-y: scroll;
    }
    
    #status.connected {
        color: $success;
    }
    
    #status.disconnected {
        color: $error;
    }
    
    #status.connecting {
        color: $warning;
    }
    """

    status: reactive[str] = reactive("Connecting…")
    status_class: reactive[str] = reactive("connecting")

    def __init__(self, port) -> None:
        super().__init__()
        self.port = port
        self.serial_instance: serial.Serial | None = None
        self.read_thread: threading.Thread | None = None
        self.running = False
        self.baud_rate = 115200
        self.reconnect_attempts = 0 
        self.auto_reconnect = True
        self.last_connect_attempt = 0.0
        logger.info(f"SerialMonitorScreen created for port: {port}")

    def compose(self) -> ComposeResult:
        with Container(id="header"):
            yield Button("Back", id="back-button", variant="primary")
            yield Static(
                f"Port: {self.port.name} - {self.port.description}", id="port-info"
            )
            yield Static(self.status, id="status", classes=self.status_class)

        with VerticalScroll(id="serial-container"):
            yield RichLog(highlight=True, markup=True, id="serial-output")

        yield Footer()

    def on_mount(self) -> None:
        logger.info("SerialMonitorScreen mounted")
        self.connect_to_port()

    def on_unmount(self) -> None:
        logger.info("SerialMonitorScreen unmounted")
        self.close_port()

    def connect_to_port(self):
        logger.info(f"Connecting to {self.port.name} @ {self.baud_rate}")
        self.status, self.status_class = "Connecting…", "connecting"
        self.last_connect_attempt = time.time()
        self.close_port()

        try:
            ser = serial.Serial()
            ser.port      = self.port.name
            ser.baudrate  = self.baud_rate
            ser.timeout   = 0.1
            ser.rtscts    = False
            ser.dsrdtr    = False

            ser.dtr = False
            ser.rts = False

            ser.open()

            self.serial_instance = ser

            self.running = True
            self.read_thread = threading.Thread(
                target=self.read_serial_data, daemon=True
            )
            self.read_thread.start()

            self.status        = f"Connected ({self.baud_rate} baud)"
            self.status_class  = "connected"
            self.reconnect_attempts = 0
            self.query_one("#serial-output", RichLog).write(
                f"[dim]{datetime.now():%H:%M:%S} - Connected[/dim]"
            )

        except Exception as exc:
            self.handle_connection_error(str(exc))

    def close_port(self):
        self.running = False

        if self.serial_instance and self.serial_instance.is_open:
            try:
                self.serial_instance.close()
            except Exception as exc:
                logger.error(f"Close error: {exc}")

        if (
            self.read_thread
            and self.read_thread.is_alive()
            and threading.current_thread() is not self.read_thread
        ):
            self.read_thread.join(timeout=1.0)

        self.serial_instance = None
        self.read_thread = None

    def read_serial_data(self):
        logger.info("Reader thread start")
        buf = ""
        while self.running and self.serial_instance:
            try:
                if not self.serial_instance.is_open:
                    self._handle_disconnection()
                    break

                data = self.serial_instance.read(1024)
                if data:
                    buf += data.decode("utf-8", errors="replace")
                    if "\n" in buf:
                        *lines, buf = buf.split("\n")
                        for ln in lines:
                            ts = datetime.now().strftime("%H:%M:%S")
                            self.add_to_log(f"[{ts}] {ln}")
                else:
                    time.sleep(0.01)

            except Exception as exc:
                logger.error(f"Reader exception: {exc}")
                self._handle_disconnection()
                break
        logger.info("Reader thread end")

    def add_to_log(self, text: str):
        if self.is_mounted:
            self.app.call_from_thread(self._update_log, text)

    def _update_log(self, text: str):
        self.query_one("#serial-output", RichLog).write(text)

    def _handle_disconnection(self):
        self.app.call_from_thread(self._update_connection_status, "Disconnected", "disconnected")
        if self.auto_reconnect:
            self.reconnect_attempts += 1
            self._attempt_reconnect()

    def _update_connection_status(self, status: str, cls: str):
        self.status = status
        self.status_class = cls
        self.query_one("#serial-output", RichLog).write(
            f"[dim]{datetime.now():%H:%M:%S} - {status}[/dim]"
        )

    def _attempt_reconnect(self):
        logger.info(f"Attempting to reconnect (attempt {self.reconnect_attempts})")
        while time.time() - self.last_connect_attempt < 2:
            logger.info(f"Waiting for reconnect cooldown... {time.time() - self.last_connect_attempt:.2f}s")
            time.sleep(0.1)
        self._update_connection_status(
            f"Reconnecting (attempt {self.reconnect_attempts})…",
            "connecting",
        )
        self.connect_to_port()

    def handle_connection_error(self, msg: str):
        self.status, self.status_class = "Disconnected", "disconnected"
        self.query_one("#serial-output", RichLog).write(
            f"[red]{datetime.now():%H:%M:%S} - {msg}[/red]"
        )
        logger.error(f"Connection error: {msg}, {self.auto_reconnect}")

        if self.auto_reconnect:
            self.reconnect_attempts += 1
            self._attempt_reconnect()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-button":
            self.action_go_back()

    async def action_change_baud_rate(self):
        modal = BaudRateModal(self.baud_rate)
        new_rate = await self.app.push_screen(modal)
        if new_rate and new_rate != self.baud_rate:
            self.baud_rate = new_rate
            self.connect_to_port()

    def action_go_back(self):
        self.close_port()
        self.app.pop_screen()
