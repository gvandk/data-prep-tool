import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt6.QtCore import Qt

class ExperimentApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Testing App")
        self.resize(500, 300)

        layout = QVBoxLayout()
        self.setLayout(layout)

        label = QLabel("This is a test application for PyQt6.")
        label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.text = QTextEdit()
        layout.addWidget(label)
        layout.addWidget(self.text)
        self.counter = 0

        button = QPushButton("Click!")

        
        button.clicked.connect(self.on_button_clicked)
        layout.addWidget(button)

    def on_button_clicked(self):
        self.counter += 1
        self.text.setText("Button clicked {} times".format(self.counter))
        print("Button clicked")

print("Before starting app", flush=True)

app = QApplication(sys.argv)
window = ExperimentApp()
window.show()

print("Right before event loop", flush=True)
sys.exit(app.exec())
print("This will never run")
