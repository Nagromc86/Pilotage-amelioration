import sys
from PyQt5.QtWidgets import QApplication, QWidget, QTabWidget, QVBoxLayout, QPushButton, QLabel
def main():
    app = QApplication(sys.argv)
    w = QWidget()
    layout = QVBoxLayout(w)
    tabs = QTabWidget()
    layout.addWidget(tabs)
    # Live (Mix)
    tw1 = QWidget(); l1 = QVBoxLayout(tw1); l1.addWidget(QLabel('Live (Mix)'))
    tabs.addTab(tw1, 'Live (Mix)')
    # CR & ToDo
    tw2 = QWidget(); l2 = QVBoxLayout(tw2); l2.addWidget(QLabel('CR & ToDo'))
    tabs.addTab(tw2, 'CR & ToDo')
    # Export
    tw3 = QWidget(); l3 = QVBoxLayout(tw3)
    l3.addWidget(QPushButton('Export : Excel (CR, ToDo, ToDo_Global)'))
    l3.addWidget(QPushButton('Export : Excel (CR formatés — tableaux)'))
    l3.addWidget(QLabel('Prêt à intégrer votre logique.'))
    tabs.addTab(tw3, 'Export')
    # Paramètres
    tw4 = QWidget(); l4 = QVBoxLayout(tw4); l4.addWidget(QLabel('Paramètres'))
    tabs.addTab(tw4, 'Paramètres')
    w.setWindowTitle('CHAP1 — Compte-rendus Harmonisés et Assistance au Pilotage 1')
    w.resize(960, 640)
    w.show()
    sys.exit(app.exec_())
