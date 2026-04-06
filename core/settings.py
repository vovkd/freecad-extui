from PySide import QtWidgets, QtCore, QtGui

import FreeCAD as App
from FreeCAD import Console

from .constants import DEFAULT_WORKBENCH, Workbenches


class SettingsWindow(QtWidgets.QDialog):
    def __init__(self, storage):
        import FreeCADGui as Gui

        super().__init__(Gui.getMainWindow())
        self.setWindowTitle("Настройки ExUI.")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        self._storage = storage
        self._storage.active_wb = Workbenches.PD
        self._storage.workbenches = self._list_workbenches()
        self.init_ui()

    def _list_workbenches(self):
        import FreeCADGui as Gui

        workbenches = Gui.listWorkbenches()
        return {workbenches[name].MenuText: name for name in sorted(workbenches)}

    def init_ui(self):
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        general_gb = self._build_general_group()
        self.layout.addWidget(general_gb, alignment=QtCore.Qt.AlignTop)

    def _build_general_group(self):
        select_wb_lbl = QtGui.QLabel("Workbench")
        select_wb_lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        select_wb_wdg = QtGui.QComboBox()
        select_wb_wdg.setMaxVisibleItems(10)
        select_wb_wdg.setStyleSheet("QComboBox { combobox-popup: 0; }")
        select_wb_wdg.setMinimumWidth(140)
        select_wb_wdg.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        select_wb_wdg.addItems(self._storage.workbenches)

        general_gb = QtGui.QGroupBox("General")
        general_gb_lyt = QtGui.QHBoxLayout()
        general_gb_lyt.addWidget(select_wb_lbl)
        general_gb_lyt.addWidget(select_wb_wdg)
        general_gb.setLayout(general_gb_lyt)
        general_gb.setMinimumWidth(300)

        return general_gb
