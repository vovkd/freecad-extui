import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets, QtGui

translate = App.Qt.translate


class Menu:
    def __init__(self, name: str, items: dict):
        self.name = name
        self.action_name = f"{self.name}Menu"
        self.window = Gui.getMainWindow()
        self._items = items
        self._build_menu(self.name)

    def _trigger_action(self, callback: callable):
        callback()

    def _build_action(self, name, callback):
        option_action = QtGui.QAction(self.window)
        option_action.setText(translate(self.action_name, f"{name} settings"))
        option_action.setObjectName(name)
        option_action.triggered.connect(callback)
        return option_action

    def _build_menu(self, name: str) -> None:
        self.window = Gui.getMainWindow()
        action = self.window.findChild(QtGui.QAction, self.action_name)

        for action_name, action_callback in self._items.items():
            option_action = self._build_action(
                action_name, lambda: self._trigger_action(action_callback)
            )

            if action:
                menu = action.menu()
                menu.addAction(option_action)
            else:
                menubar = self.window.menuBar()

                action = QtGui.QAction(self.window)
                action.setObjectName(self.action_name)
                action.setIconText(translate("FreeCAD Menu", self.name))

                menu = QtGui.QMenu()
                action.setMenu(menu)
                menu.addAction(option_action)

                def add_action():
                    menubar.addAction(action)
                    action.setVisible(True)

                add_action()
                self.window.workbenchActivated.connect(add_action)
