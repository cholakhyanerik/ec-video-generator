DARK_THEME = """
QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
}

QGroupBox {
    border: 1px solid #3e3e3e;
    border-radius: 6px;
    margin-top: 20px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

QPushButton {
    background-color: #0078d4;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #2b88d8;
}

QPushButton:disabled {
    background-color: #333333;
    color: #888888;
}

QLineEdit, QComboBox {
    background-color: #2d2d2d;
    border: 1px solid #3e3e3e;
    border-radius: 4px;
    padding: 5px;
    color: white;
}

QLabel#Header {
    font-size: 18px;
    font-weight: bold;
    color: #0078d4;
}

QProgressBar {
    border: 1px solid #3e3e3e;
    border-radius: 4px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #0078d4;
}
"""