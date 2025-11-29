import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem
from PyQt6.QtCore import Qt
import pandas as pd

class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Table Viewer")
        self.resize(1000, 600)
        
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label = QLabel("TABLE VIEWER \n click on a cell to print its value.")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)

        self.table.setColumnCount(df.shape[1])
        self.table.setRowCount(df.shape[0])
        self.table.setHorizontalHeaderLabels(df.columns)
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                self.table.setItem(i, j, QTableWidgetItem(str(df.iat[i, j])))

        self.table.cellClicked.connect(self.cell_clicked)
                
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.table)

    def cell_clicked(self, row, column):
        value = self.table.item(row, column).text()
        print(f"You clicked: row={row}, col={column}, value={value}", flush=True)


df = pd.read_csv("generated_dataset.csv")

app = QApplication(sys.argv)
window = MyApp()
window.show()
sys.exit(app.exec())