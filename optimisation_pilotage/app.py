import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QWidget, QTabWidget, QVBoxLayout, QPushButton, QLabel
def main():
    app = QApplication(sys.argv)
    w = QWidget(); layout = QVBoxLayout(w); tabs = QTabWidget(); layout.addWidget(tabs)
    # Live tab stub
    tw1 = QWidget(); l1 = QVBoxLayout(tw1); l1.addWidget(QLabel('Live (Mix)'))
    tabs.addTab(tw1, 'Live (Mix)')
    # CR/ToDo stub
    tw2 = QWidget(); l2 = QVBoxLayout(tw2); l2.addWidget(QLabel('CR & ToDo'))
    tabs.addTab(tw2, 'CR & ToDo')
    # Export tab
    tw3 = QWidget(); l3 = QVBoxLayout(tw3); b=QPushButton('Export : Excel (CR, ToDo, ToDo_Global)'); l3.addWidget(b)
    b2=QPushButton('Export : Excel (CR formatés — tableaux)'); l3.addWidget(b2); msg=QLabel(''); l3.addWidget(msg)
    tabs.addTab(tw3, 'Export')
    # Paramètres tab
    tw4 = QWidget(); l4 = QVBoxLayout(tw4); l4.addWidget(QLabel('Paramètres')); tabs.addTab(tw4, 'Paramètres')
    w.setWindowTitle('CHAP1 — Compte-rendus Harmonisés et Assistance au Pilotage 1')
    w.resize(960,640); w.show(); sys.exit(app.exec_())
