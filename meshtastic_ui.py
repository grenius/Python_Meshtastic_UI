import sys
import threading
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QPushButton,
    QTextEdit,
    QLineEdit,
    QWidget,
    QListWidget,
    QHBoxLayout,
    QLabel,
    QSplitter,
)
from PyQt5.QtCore import Qt
import meshtastic
from meshtastic.serial_interface import SerialInterface
from meshtastic import mesh_pb2


class MeshtasticApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.apply_dark_mode()
        self.interface = None
        self.log_file = "messages.log"

    def initUI(self):
        self.setWindowTitle("Meshtastic UI - Dark Mode")
        self.setGeometry(100, 100, 1000, 600)

        # Main Layout
        main_layout = QVBoxLayout()

        # Top Controls: Connect Button
        self.connect_button = QPushButton("Connect to Meshtastic")
        self.connect_button.clicked.connect(self.connect_to_device)
        main_layout.addWidget(self.connect_button)

        # Splitter for Node List and Messages
        splitter = QSplitter(Qt.Horizontal)

        # Node List Section
        node_layout = QVBoxLayout()
        self.node_list_label = QLabel("Connected Nodes")
        self.node_list = QListWidget()
        self.node_list.addItem("Nodes will appear here...")
        node_layout.addWidget(self.node_list_label)
        node_layout.addWidget(self.node_list)
        node_widget = QWidget()
        node_widget.setLayout(node_layout)
        splitter.addWidget(node_widget)

        # Messages Section
        message_layout = QVBoxLayout()
        self.message_list_label = QLabel("Received Messages")
        self.message_list = QTextEdit()
        self.message_list.setReadOnly(True)
        self.message_list.setPlaceholderText("Incoming messages will appear here...")
        message_layout.addWidget(self.message_list_label)
        message_layout.addWidget(self.message_list)

        # Load Messages Button
        self.load_button = QPushButton("Load Messages")
        self.load_button.clicked.connect(self.load_messages_from_file)
        message_layout.addWidget(self.load_button)

        message_widget = QWidget()
        message_widget.setLayout(message_layout)
        splitter.addWidget(message_widget)

        main_layout.addWidget(splitter)

        # Bottom Controls: Message Input and Send Button
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message to send...")
        self.send_button = QPushButton("Send Message")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        main_layout.addLayout(input_layout)

        # Set Layout
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def apply_dark_mode(self):
        """Apply a dark mode theme to the UI."""
        dark_stylesheet = """
        QMainWindow {
            background-color: #2b2b2b;
        }
        QLabel {
            color: #ffffff;
        }
        QListWidget {
            background-color: #3c3f41;
            color: #ffffff;
        }
        QTextEdit {
            background-color: #3c3f41;
            color: #ffffff;
            border: 1px solid #5c5c5c;
        }
        QLineEdit {
            background-color: #3c3f41;
            color: #ffffff;
            border: 1px solid #5c5c5c;
        }
        QPushButton {
            background-color: #3c3f41;
            color: #ffffff;
            border: 1px solid #5c5c5c;
        }
        QPushButton:hover {
            background-color: #505357;
        }
        """
        self.setStyleSheet(dark_stylesheet)

    def connect_to_device(self):
        try:
            self.log_message("Connecting to Meshtastic device on /dev/ttyACM0...")
            self.interface = SerialInterface(devPath="/dev/ttyACM0")
            self.interface.onReceive = self.on_message_received
            self.output_nodes()
            self.log_message("Connected to Meshtastic device!")
        except Exception as e:
            self.log_message(f"Error connecting to device: {str(e)}")

    def on_message_received(self, packet, interface):
        """Callback to handle incoming messages."""
        try:
            # Debugging: Log the full packet
            self.log_message(f"Raw packet received: {packet}")

            # Check if the packet is a text message
            if packet["decoded"]["portnum"] == mesh_pb2.PortNum.TEXT_MESSAGE_APP:
                message = packet["decoded"]["payload"].decode("utf-8")
                sender = packet["from"]
                parsed_message = f"Message from {sender}: {message}"
                self.log_message(parsed_message)

                # Save to log file
                with open(self.log_file, "a") as log_file:
                    log_file.write(parsed_message + "\n")
            else:
                self.log_message("Received a non-text packet.")
        except KeyError as e:
            self.log_message(f"Missing key in packet: {str(e)}")
        except UnicodeDecodeError:
            self.log_message("Error decoding message payload.")
        except Exception as e:
            self.log_message(f"Error processing message: {str(e)}")

    def load_messages_from_file(self):
        """Load messages from the log file and display them in the GUI."""
        try:
            self.message_list.clear()
            with open(self.log_file, "r") as log_file:
                messages = log_file.readlines()
                for message in messages:
                    self.message_list.append(message.strip())
        except FileNotFoundError:
            self.log_message("No message log file found.")
        except Exception as e:
            self.log_message(f"Error loading messages: {str(e)}")

    def output_nodes(self):
        """Display connected nodes."""
        if self.interface:
            self.node_list.clear()
            self.node_list.addItem("Connected Nodes:")
            for node_id, node in self.interface.nodes.items():
                node_name = node.get("user", {}).get("longName", "Unknown Node")
                self.node_list.addItem(f"{node_id}: {node_name}")
                self.log_message(f"Node {node_id}: {node_name}")
        else:
            self.log_message("Device not connected. Please connect first.")

    def send_message(self):
        """Send a message to the network."""
        if self.interface:
            message = self.message_input.text().strip()
            if message:
                self.interface.sendText(message)
                self.log_message(f"Sent message: {message}")
                self.message_input.clear()
            else:
                self.log_message("Cannot send an empty message.")
        else:
            self.log_message("Device not connected. Please connect first.")

    def log_message(self, message):
        """Log a message to both the GUI and the terminal."""
        print(message)  # Print to terminal
        self.message_list.append(message)  # Add to GUI

    def closeEvent(self, event):
        """Handle application close."""
        if self.interface:
            self.interface.close()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MeshtasticApp()
    window.show()
    sys.exit(app.exec_())
