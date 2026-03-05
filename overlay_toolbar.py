from importlib import import_module

from PySide import QtWidgets, QtCore
from PySide.QtGui import QAction

import FreeCADGui as Gui
from FreeCAD import Console

style = """
    background: rgba(45, 45, 45, 220);
    border-radius: 8px;
"""

btn_width = 40
btn_height = 28

button_style = f"""
    QPushButton {{
            background-color: transparent;
            border: none;
            width: {btn_width}px;
            height: {btn_height}px;
            border-radius: 8px;
        }}
    QPushButton:hover {{
        background-color: rgba(255, 255, 255, 50);
        border-radius: 4px;
    }}
    QPushButton:pressed {{
        background-color: rgba(255, 255, 255, 80);

    }}
"""

tool_button_style = """
    QToolButton {
        background-color: transparent;
        border-radius: 4px;
        padding: 1px;
        padding-right: 12px;
        width: 40px;
        height: 30px;
    }
    QToolButton:hover {
        background-color: #505050;
    }
    QToolButton:pressed {
        background-color: #505050;
    }
    QToolButton::menu-indicator {
        subcontrol-origin: padding;
        subcontrol-position: center right;
        background-color: transparent;
        bottom: 2px;
    }
    QToolButton::menu-button {
        width: 12px;
        padding: 0 1px;
        background: transparent;
    }

    QToolButton::menu-button:hover {
        background: transparent;
    }
"""

menu_style = """
    QMenu {
        background-color: #2b2b2b;
        color: #e0e0e0;          
        border: 1px solid transparent;
        padding: 10px;             
        margin-top: 1px;
        border-radius: 10px; 
    }
    QMenu::item {
        background-color: transparent;
        padding: 6px 10px 6px 5px;
        border: 1px solid transparent;
    }
    QMenu::item:selected {
        background-color: #6a6a6a;
        color: white;
        border-radius: 3px;
    }
    QMenu::item:disabled {
        color: #666;       
    }
"""



tools = (
    # ( <workbench name>, <tool name>, (<command signature>, <cmd param1>..<cmd paramN>), <icon name>)
    (
        ('PartDesign', 'NewSketch', ('PartDesign_NewSketch', ), 'Sketcher_NewSketch'),
    ),    
    (
        ('Sketcher', 'ValidateSketch', ('Sketcher_ValidateSketch', ), 'Sketcher_ValidateSketch'),
    ),    
    (
        ('Part', '0 Isometric', ('Std_ViewIsometric',), 'view-axonometric'),
        ('Part', '1 Front', ('Std_ViewFront', ), 'view-front'),
        ('Part', '2 Top', ('Std_ViewTop', ), 'view-top'),
        ('Part', '3 Right', ('Std_ViewRight', ), 'view-right'),
        ('Part', '4 Rear', ('Std_ViewRear', ), 'view-rear'),
        ('Part', '5 Bottom', ('Std_ViewBottom', ), 'view-bottom'),
        ('Part', '6 Left', ('Std_ViewLeft', ), 'view-left'),
    ),
    (
        ('Part', 'Coordinate system', ('Part_CoordinateSystem', ), 'Std_CoordinateSystem'),
        ('Std', 'Datum Plane', ('Part_DatumPlane', ), 'Std_Plane'),
        ('Std', 'Datum Line', ('Part_DatumLine', ), 'Std_Axis'),
        ('Std', 'Datum Point', ('Part_DatumPoint', ), 'Std_Point'),
    ),    
    (
        ('Part', 'Align to selection', ('Std_AlignToSelection', ), 'align-to-selection'),
    ),    
    (
        ('Part', 'Fit All', ('Std_ViewFitAll', ), 'zoom-all'),
        ('Part', 'Fit All', ('Std_ViewFitSelection', ), 'zoom-selection'),
    ),    
    (
        ('Std', '1 As is', ('Std_DrawStyle', 0), 'DrawStyleAsIs'),
        ('Std', '2 Point', ('Std_DrawStyle', 1), 'DrawStylePoints'),
        ('Std', '3 Wireframe', ('Std_DrawStyle', 2), 'DrawStyleWireFrame'),
        ('Std', '4 Hidden Line', ('Std_DrawStyle', 3), 'DrawStyleHiddenLine'),
        ('Std', '5 No Shading', ('Std_DrawStyle', 4), 'DrawStyleNoShading'),
        ('Std', '6 Shaded', ('Std_DrawStyle', 5), 'DrawStyleShaded'),
        ('Std', '7 Flat Lines', ('Std_DrawStyle', 6), 'DrawStyleFlatLines'),
    ),
)


class MatrixShapeWidget(QtWidgets.QWidget):
    def __init__(self, parent, widgets, rows=5, cols=5):
        super().__init__()
        self.layout = QtWidgets.QGridLayout(parent)
        self.layout.setContentsMargins(5, 0, 7, 0)
        self.layout.setSpacing(1)
        self.layout.setVerticalSpacing(2)
        self.widgets = widgets
        if rows == 1:
            self.cols = len(self.widgets)
            self.rows = rows
        else:
            self.cols = cols
            self.rows = rows
        self.generate_matrix(self.rows, self.cols)


    def generate_matrix(self, rows, cols):
        for idx in reversed(range(self.layout.count())): 
            self.layout.itemAt(idx).widget().setParent(None)

        for idx, tool in enumerate(self.widgets):
            row = idx // self.cols
            col = idx % self.cols
            self.layout.addWidget(tool, row, col)


class ResizeFilter(QtCore.QObject):
    def __init__(self, target_widget, widget, callback=None):
        super().__init__()
        self.target = target_widget 
        self.widget = widget
        self.callback = callback

    def eventFilter(self, obj, event):
        if obj == self.target and event.type() == QtCore.QEvent.Resize:
            self.callback()
        return super().eventFilter(obj, event)


# class DocumentObserver:
#     def openDocument(self, docName):
#         # Code to run when a document is opened
#         print(f"Document {docName} opened!")
#         # Call your main macro functionality here

#     def activateDocument(self, docName):
#         # Code to run when a document is activated
#         print(f"Document {docName} activated!")

# # Create an instance of the observer and register it
# observer = DocumentObserver()
# App.addDocumentObserver(observer)


class OverlayPanel(QtWidgets.QWidget):
    def __init__(
        self,
        tools: tuple = tools,
        parent=None,
        style: dict | None = None, 
    ) -> None:

        super().__init__(parent)
        self._gui = Gui
        self._tools = tools
        self._margin_top = 10
        self._button_style = style.get('button') if style else ''
        self._box_style = style.get('box') if style else ''
        
        flags = (
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.SubWindow
        )
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._view_widget = self._get_3dview_widget()
        
        self._overlay = QtWidgets.QFrame(self._view_widget)
        self.layouts = {
            'matrix': lambda widgets, cols: MatrixShapeWidget(self._overlay, widgets, cols=cols),
            'line': lambda widgets, cols: MatrixShapeWidget(self._overlay, widgets, rows=1) 
        }
        self.default_layout = self.layouts['line']
        self._build_buttons(self.default_layout)        

        self._resize_filter = ResizeFilter(self._view_widget, self._overlay, self.update)
        self._view_widget.installEventFilter(self._resize_filter)

    # def _build_layout(self):
    #     self._layout = QtWidgets.QHBoxLayout(self._overlay)
    #     self._layout.setContentsMargins(5, 0, 7, 0)
    #     self._layout.setSpacing(1)

    # def rebuild(self, tools = None, layout: str = None):
    #     self.hide()
    #     if tools:
    #         self._tools = tools

    #     def recursive_delete(widget):
    #         if not widget.layout():
    #             return False
            
    #         layout = widget.layout()
            
    #         while layout.count():
    #             item = layout.takeAt(0)
    #             if item.widget():
    #                 item.widget().deleteLater()
    #             elif item.layout():
    #                 recursive_delete(item.layout())
         
    #     recursive_delete(self._layout.layout())
    #     self._layout.deleteLater()
    #     self._overlay.setLayout(None)
    #     layout = self.layouts.get(layout)
    #     self._build_buttons(self.default_layout)
    #     self.show()
    
    def _make_pushbutton(self, command: list) -> QtWidgets.QPushButton:
        workbench, name, cmd, icon_name = command
        if workbench not in ['Std']:
            import_module(workbench)
        icon = self._gui.getIcon(icon_name)
        btn = QtWidgets.QPushButton('')
        if icon: 
            btn.setIcon(icon)
        else: 
            btn.setText('?')
        btn.setFlat(True)
        btn.setIconSize(QtCore.QSize(24, 24))
        btn.setStyleSheet(button_style)
        btn.clicked.connect(lambda checked=False, c=cmd: self.run_cmd(c))

        return btn

    def _make_qaction(self, command: list) -> QAction:
        workbench, name, cmd, icon_name = command
        if workbench not in ['Std']:
            import_module(workbench)

        icon = self._gui.getIcon(icon_name) 

        btn = QAction(name, self)
        if icon: 
            btn.setIcon(icon)
        else: 
            btn.setText(name)
        btn.triggered.connect(lambda checked=False, c=cmd: self.run_cmd(c))
        return btn
    
    def _make_toolbutton(self, command: list) -> QtWidgets.QToolButton:
        workbench, name, cmd, icon_name = command
        if workbench not in ['Std']:
            import_module(workbench)
        group_btn = QtWidgets.QToolButton(self._overlay)

        icon = self._gui.getIcon(icon_name) 
        group_btn.setIcon(icon)
        group_btn.setIconSize(QtCore.QSize(24, 24))
        group_btn.setAutoRaise(True)
        group_btn.setMinimumWidth(50)
        group_btn.setStyleSheet(tool_button_style)
        group_btn.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        group_btn.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        callback = lambda checked=False, c=cmd: self.run_cmd(c)
        group_btn.clicked.connect(callback)
        return group_btn

    def _on_menu_triggered(self, btn, action):
        btn.setIcon(action.icon()) 
        btn.setText(action.text())
        btn.setChecked(False)
        btn.clicked.disconnect()
        btn.clicked.connect(action.trigger)

    def _build_buttons(self, layout):
        widgets = []
        for command in self._tools:
            if len(command) > 1:
                group_btn = self._make_toolbutton(command[0])

                menu = QtWidgets.QMenu(self)
                menu.setStyleSheet(menu_style)
                menu.setAttribute(QtCore.Qt.WA_TranslucentBackground)

                for cmd in command:
                    btn =self._make_qaction(cmd)
                    menu.addAction(btn)
                callback = lambda action, group=group_btn: self._on_menu_triggered(group, action)
                menu.triggered.connect(callback)
                widgets.append(group_btn)
                group_btn.setMenu(menu)
            else:
                btn = self._make_pushbutton(command[0])
                widgets.append(btn)
        self._layout = layout(widgets, cols=5).layout

    def run_cmd(self, cmd: list):
        try:
            self._gui.runCommand(*cmd)
        except Exception as e:
            print(f"Error running command '{cmd}': {e}")


    def _is_3d_view(self, sub_window):
        if not sub_window:
            Console.PrintError('No active subwindow found.\n')
            return False

        stop_list = (
            'StartWorkbench',
        )

        if self._gui.activeWorkbench().name() in stop_list:
            Console.PrintError('Current active workbench is in stop list.\n')
            return False
        widget = sub_window.widget()
        widget_stop_list = (
            'Web',
            'Help',
        )
        if widget and (widget.metaObject().className() in widget_stop_list):
            return False

        title = sub_window.windowTitle()
        title_stop_list = (
            'Start',
            'Начало',
        )
        if title in title_stop_list:
            stop_symbols = (':', '.')
            if any(sym in title for sym in stop_symbols):
                Console.PrintError('Subwindow title is in stop list.\n')
                return False

        return True            

    def _get_3dview_widget(self):
        mw = self._gui.getMainWindow()
        mdi_area = mw.findChild(QtWidgets.QMdiArea)
        if not mdi_area:
            Console.PrintError("No QMdiArea found in the main window")
            return
    
        active_sub = mdi_area.activeSubWindow()
        if not active_sub:
            Console.PrintError("No active subwindow found")
            return

        if not self._is_3d_view(active_sub):
            Console.PrintError("Active subwindow is not a 3D view")
            return
        
        return active_sub.widget()

    def _build_overlay(self):
        if self._view_widget is None:
            return

        self._overlay.setStyleSheet(style)
        self._overlay.setMinimumHeight(self._layout.rowCount() * 44)

        toolbar_width = (self._layout.columnCount() ) * (btn_width + 10) + 20
        self._overlay.setMinimumWidth(toolbar_width)
        return self._overlay


    def show(self):
        self._build_overlay()
        if self._view_widget and self._overlay:
            pos_x = (self._view_widget.width() - self._overlay.width()) // 2
            self._overlay.move(pos_x, self._margin_top)
            self._gui._sw_overlay = self._overlay
            self.adjustSize()
            self._overlay.show()
    
    def hide(self):
        self._overlay.hide()
    
    def destroy(self):
        self._view_widget.removeEventFilter(self._resize_filter)
        self._resize_filter.deleteLater()
        self._overlay.close()
        self._overlay.deleteLater()
        
    def update(self):
        pos_x = (self._view_widget.width() - self._overlay.width()) // 2
        self._overlay.move(pos_x, self._margin_top)
    


def overlay_destroy():
    app = Gui.getMainWindow()
    for child in app.children():
        if isinstance(child, OverlayPanel):
            child.destroy()

if __name__ == '__main__':

    overlay_destroy()
    app = Gui.getMainWindow()
    overlay = OverlayPanel(parent=app)
    overlay.show()