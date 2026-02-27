import math
from dataclass import dataclass
from importlib import import_module

from pivy import coin
from PySide import QtWidgets, QtCore, QtGui

import FreeCADGui as Gui
import FreeCAD as App
from FreeCAD import Console, Units

style = """
    background: rgba(120, 120, 120, 100);
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
@dataclass
class Commands:
    edit_sketch: str = 'Sketcher_EditSketch'

@dataclass
class ToolTypes:
    fillet = 'PartDesign::Fillet'
    chamfer = 'PartDesign::Chamfer'
    pad = 'PartDesign::Pad'
    pocket = 'PartDesign::Pocket'
    revolution = 'PartDesign::Revolution'
    groove = 'PartDesign::Groove'
    thickness = 'PartDesign::Thickness'

class EdgeToolOverlay(QtWidgets.QWidget):
 
    has_event_filter = False
    
    def __init__(self):
        super().__init__(Gui.getMainWindow())
        self.dist = 0
        self._pos = None
        self._cur_pos = None
        flags = (
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.SubWindow
        )
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(50, 50, 50, 100); border-radius: 5px; padding: 5px;")
        
        self.overlay = self._build_overlay_frame()
        self.layout = self._build_layout(self.overlay)
        
        self.selection_type = ''
        self.selection_name = ''
        self.spinbox = None
       
        self._setup_tools()
        self._setup_ev_filter()
        self._setup_cursor_ev_handler()
        self.hide()
        
        self.translate = App.Qt.translate
        
    def eventFilter(self, obj, event):
        edited_object = Gui.ActiveDocument.getInEdit()
        if edited_object and (event.type() == QtCore.QEvent.KeyPress):
            key = event.key()
            if key == QtCore.Qt.Key_Enter or key == QtCore.Qt.Key_Return:
                self._finish_fast_edit()
            elif key == QtCore.Qt.Key_Escape:
                self._cancel_fast_edit()
        return False

    def _setup_tools(self):
        self._tool_groups = {
            'edge': ('Fillet', 'Chamfer'),
            'face': ('Fillet', 'Chamfer', 'Pocket', 'NewSketch', 'EditSketch', 'Binder'),
            'sketch': ('ValidateSketch', 'Pad', 'Hole', 'Pocket'),
        }
    
        self._tools = (
            ('PartDesign', 'Fillet', ('PartDesign_Fillet', ), 'PartDesign_Fillet'),
            ('PartDesign', 'Chamfer', ('PartDesign_Chamfer', ), 'PartDesign_Chamfer'),
            ('PartDesign', 'Pocket', ('PartDesign_Pocket', ), 'PartDesign_Pocket'),
            ('PartDesign', 'Pad', ('PartDesign_Pad', ), 'PartDesign_Pad'),
            ('PartDesign', 'Hole', ('PartDesign_Hole', ), 'PartDesign_Hole'),
            ('PartDesign', 'NewSketch', ('PartDesign_NewSketch', ), 'Sketcher_NewSketch'),
            ('Sketcher', 'EditSketch', ('Sketcher_EditSketch',), 'Sketcher_EditSketch'),
            ('Sketcher', 'ValidateSketch', ('Sketcher_ValidateSketch',), 'Sketcher_ValidateSketch'),
            ('PartDesign', 'Binder', ('PartDesign_SubShapeBinder',), 'PartDesign_SubShapeBinder'),
        )
        
        for tool in self._tools:
            btn = self._make_pushbutton(tool)
            self.layout.addWidget(btn)

    def _setup_ev_filter(self):
        if not self.__class__.has_event_filter:
            app = QtGui.QGuiApplication.instance() or QtGui.QApplication([])
            app.installEventFilter(self)
            self.__class__.has_event_filter = True
        
    def _setup_cursor_ev_handler(self):
        view = Gui.ActiveDocument.ActiveView
        view.addEventCallbackPivy(coin.SoEvent.getClassTypeId(), self._mouse_ev_callback)

    def _build_overlay_frame(self):
        overlay = QtWidgets.QFrame(self.parent())
        overlay.setFixedHeight(46)        
        overlay.setStyleSheet(style)
        opacity_effect = QtWidgets.QGraphicsOpacityEffect()
        overlay.setGraphicsEffect(opacity_effect)
        overlay.graphicsEffect().setOpacity(1)
        return overlay
    
    def _build_layout(self, overlay: QtWidgets.QFrame):
        layout = QtWidgets.QHBoxLayout(overlay)
        layout.setContentsMargins(5, 0, 7, 0)
        layout.setSpacing(1)
        return layout

    def build_spinbox(self, buttonSize=32, step=1.0):
        """ https://github.com/FreeCAD/FreeCAD/blob/main/src/Gui/QuantitySpinBox.h """
        ui = Gui.UiLoader()
        spinbox = ui.createWidget('Gui::QuantitySpinBox')
        spinbox.setProperty('minimum', 0.0)
        spinbox.setProperty('minimum', 0.0)
        # spinbox.setMinimumWidth(200)
        spinbox.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        spinbox.setProperty('ButtonX', 0)
        spinbox.setProperty('ButtonY', -30)
        spinbox.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # spinbox.setStyleSheet(' QWidget { border-radius: 5px; width: 150px;}')
        spinbox.setProperty('setSingleStep', step)
        Console.PrintMessage('Build Spinbox...Ok!\n')
        return spinbox

    def _build_throughall_checkbox(self):
        control = QtWidgets.QCheckBox(self.translate('Fast Spinbox', 'Through all'))
        control.setCheckable(True)
        control.setProperty('ButtonX', 50)
        control.setProperty('ButtonY', -105)
        control.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        return control

    def _build_reversed_checkbox(self):
        control = QtWidgets.QCheckBox(self.translate('Fast Spinbox', 'Reversed'))
        control.setCheckable(True)
        control.setProperty('ButtonX', 50)
        control.setProperty('ButtonY', -55)
        control.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        return control

    def _build_sym2plane_checkbox(self):
        control = QtWidgets.QCheckBox(self.translate('Fast Spinbox', 'Symmetric to plane'))
        control.setCheckable(True)
        control.setProperty('ButtonX', 50)
        control.setProperty('ButtonY', -80)
        control.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        return control

    def _build_checkbox(self, checkbox, attr='Type', obj_type=True):
        edited_object = Gui.ActiveDocument.getInEdit()
        
        checkbox.setParent(self.fast_edit_overlay)
        checkbox.setObjectName('styleCheckbox')
        checkbox.setStyleSheet('QWidget {background: transparent;}')
        checkbox.stateChanged.connect(self._fast_edit_callback)

        if getattr(edited_object.Object, attr) == obj_type:
            checkbox.setChecked(True)
        else:
            checkbox.setChecked(False)
        return checkbox

    def _fast_edit_callback(self):
            doc = App.ActiveDocument
            edited_object = Gui.ActiveDocument.getInEdit()
            if edited_object is None:
                return
            active_tool = edited_object.Object

            value = self.spinbox.property('value')
            Console.PrintMessage(f'active tool 1 {active_tool}')
            
            is_midplane_checked = self.midplane_checkbox.isChecked() if hasattr(self, 'midplane_checkbox') else 0
            is_reversed_checked = self.reversed_checkbox.isChecked() if hasattr(self, 'reversed_checkbox') else 0


            Console.PrintMessage(f'ed obj: {edited_object.Object.TypeId}\n')
            if active_tool.TypeId == ToolTypes.fillet:
                doc.getObject(active_tool.Name).Radius = value

            elif active_tool.TypeId in ToolTypes.chamfer:
                doc.getObject(active_tool.Name).Size = value

            elif active_tool.TypeId == ToolTypes.pocket:
                Console.PrintMessage(f'ed obj: {edited_object.Object.TypeId}\n')
                doc.getObject(active_tool.Name).SideType = is_midplane_checked
                doc.getObject(active_tool.Name).Reversed = is_reversed_checked
                doc.getObject(active_tool.Name).Length = value

            elif active_tool.TypeId == ToolTypes.pad:
                doc.getObject(active_tool.Name).SideType = is_midplane_checked
                doc.getObject(active_tool.Name).Reversed = is_reversed_checked
                doc.getObject(active_tool.Name).Length = value

            elif active_tool.TypeId == ToolTypes.thickness:
                doc.getObject(active_tool.Name).Value = value

            elif active_tool.TypeId == ToolTypes.revolution:
                doc.getObject(active_tool.Name).Angle = value

            elif active_tool.TypeId == ToolTypes.groove:
                doc.getObject(active_tool.Name).Angle = value

            doc.recompute()
            
    def _finish_fast_edit(self):
        Console.PrintMessage(f'STOP OPERTATIO\n')
        Gui.runCommand('Sketcher_StopOperation')
        Gui.ActiveDocument.resetEdit()
        App.ActiveDocument.recompute()
        if hasattr(self, 'self.fast_edit_overlay'):
            self.fast_edit_overlay.hide()
        self.hide()

    def _cancel_fast_edit(self):
        docName = App.ActiveDocument.Name
        # quit current sketcher operation:
        Gui.runCommand('Sketcher_StopOperation')
        App.closeActiveTransaction(True)
        Gui.Control.closeDialog()
        App.getDocument(docName).recompute()
        Gui.getDocument(docName).resetEdit()
        if hasattr(self, 'self.fast_edit_overlay'):
            self.fast_edit_overlay.hide()
        self.hide()
    
    def build_fast_edit(self):

        is_visible = False
        active_tool = None

        self.fast_edit_overlay = QtWidgets.QFrame(self.parent())
        self.fast_edit_overlay.setStyleSheet(style)
        self.fast_edit_overlay.setMinimumHeight(46)
        self.fast_edit_overlay.setMinimumWidth(50)

        self.fast_edit_layout = QtWidgets.QVBoxLayout(self.fast_edit_overlay)
        self.fast_edit_layout.setContentsMargins(5, 5, 5, 5)
        self.fast_edit_layout.setSpacing(1)
        
        edited_object = Gui.ActiveDocument.getInEdit()
        if edited_object:
            active_tool = edited_object.Object

            self.spinbox = self.build_spinbox()
            
            if active_tool.TypeId == ToolTypes.fillet:
                value = Units.Quantity(active_tool.Radius) or Units.Quantity(1)
                value = Units.Quantity(value.getUserPreferred()[0])        
                Gui.ExpressionBinding(self.spinbox).bind(active_tool, 'Radius')
                is_visible = True

            elif active_tool.TypeId == ToolTypes.chamfer:
                value = Units.Quantity(active_tool.Size)
                value = Units.Quantity(value.getUserPreferred()[0])        
                Gui.ExpressionBinding(self.spinbox).bind(active_tool, 'Size')
                is_visible = True

            elif active_tool.TypeId == ToolTypes.thickness:
                value = Units.Quantity(active_tool.Value)
                value = Units.Quantity(value.getUserPreferred()[0])        
                Gui.ExpressionBinding(self.spinbox).bind(active_tool, 'Value')
                is_visible = True

            tools = (
                ToolTypes.pad,
                ToolTypes.pocket,
                ToolTypes.groove,
                ToolTypes.revolution,
            )

            if active_tool.TypeId in tools:
                if active_tool.TypeId in (ToolTypes.pocket, ToolTypes.pad):
                    value = Units.Quantity(active_tool.Length)
                    value = Units.Quantity(value.getUserPreferred()[0])        
                    Gui.ExpressionBinding(self.spinbox).bind(active_tool, 'Length')
                    is_visible = True

                    sym2plane_checkbox = self._build_sym2plane_checkbox()
                    self.midplane_checkbox = self._build_checkbox(sym2plane_checkbox, 'Midplane', True)
                    self.midplane_checkbox.setVisible(True)

                    checkbox_reversed = self._build_reversed_checkbox()
                    self.reversed_checkbox = self._build_checkbox(checkbox_reversed, 'Reversed', True)
                    self.reversed_checkbox.setVisible(True)
                    
                    self.fast_edit_layout.addWidget(self.midplane_checkbox)
                    self.fast_edit_layout.addWidget(self.reversed_checkbox)

            if is_visible:
                self.spinbox.setFocusPolicy(QtCore.Qt.StrongFocus)
                QtCore.QTimer.singleShot(0, self.spinbox.setFocus)
                QtCore.QTimer.singleShot(0, self.spinbox.selectAll)
                self.spinbox.setProperty('value', value)
                self.spinbox.valueChanged.connect(self._fast_edit_callback)
                self.spinbox.setVisible(True)
                self.spinbox.show()

                self.fast_edit_overlay.move(self.overlay.x(), self.overlay.y())
                self.fast_edit_layout.addWidget(self.spinbox)
                self.fast_edit_overlay.adjustSize() 
                self.fast_edit_overlay.show()
                self.fast_edit_overlay.move(self._get_cursor_pos())
                QtGui.QCursor.setPos(self.overlay.parent().mapToGlobal(self._get_cursor_pos()))
        
    def set_selection(self, doc, name, selection_type):
        self.selection_type = selection_type
        self.selection_name = name
        self.selection_doc = doc

    def set_overay_width(self, count):
        toolbar_width = (count) * (btn_width + 10) + 20
        self.overlay.setMinimumWidth(toolbar_width)
        self.overlay.setFixedWidth(toolbar_width)

    def _get_sketch(self):
        obj = App.getDocument(self.selection_doc).getObject(self.selection_name.split('.')[0])
        type_id = 'Sketcher::SketchObject'
        sketch = [item for item in obj.OutList if item.TypeId == type_id]
        if sketch:
            return sketch[0]
        else:
            objs = App.ActiveDocument.Objects[:]
            objs.reverse()
            for obj in objs:
                if obj.TypeId == "Sketcher::SketchObject":
                    return obj
                    
    def update(self):
        counter_enabled = 0
        self.set_overay_width(counter_enabled)
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            
            if widget and widget._name not in self._tool_groups[self.selection_type]:
                widget.hide()
            elif not self._get_sketch() and widget._name == 'EditSketch':
                    widget.hide()
            else:
                counter_enabled += 1
                widget.show()
        self.set_overay_width(counter_enabled)

    def run_cmd(self, cmd, args=None):
        
        if cmd[0] == Commands.edit_sketch:
            sketch = self._get_sketch()
            Gui.Selection.clearSelection()
            Gui.Selection.addSelection(self.selection_doc, sketch.Name)

        Gui.runCommand(*cmd)
        self.hide()
        self.build_fast_edit()
        
    def clear_selection(self):
        Gui.Selection.clearSelection()
        self.selection_type = ''
        self.selection_name = ''

    def _make_pushbutton(self, command: list) -> QtWidgets.QPushButton:
        workbench, name, cmd, icon_name = command
        if workbench not in ['Std']:
            import_module(workbench)
        icon = Gui.getIcon(icon_name)
        btn = QtWidgets.QPushButton('')
        if icon: 
            btn.setIcon(icon)
            btn._name = name
        else: 
            btn.setText('?')
        btn.setFlat(True)
        btn.setIconSize(QtCore.QSize(24, 24))
        btn.setStyleSheet(button_style)
        btn.clicked.connect(lambda checked=False, c=cmd: self.run_cmd(c))

        return btn

    def _get_cursor_pos(self):
        pos = QtGui.QCursor.pos()
        widget = self.overlay.parent()
        return widget.mapFromGlobal(pos)
        
    
    def _distance(self, cursor_pos: QtCore.QPoint):
        x_dist = abs(self._pos.x()) - abs(cursor_pos.x())
        y_dist = abs(self._pos.y()) - abs(cursor_pos.y())
        return math.hypot(x_dist, y_dist)

    def _mouse_ev_callback(self, data, frequency=5):
        if not hasattr(self.__class__._mouse_ev_callback, 'counter'):
            setattr(self.__class__._mouse_ev_callback, 'counter', 0)

        if self.__class__._mouse_ev_callback.counter % frequency == 0:
            event = data.getEvent()
            pos = event.getPosition().getValue()
            if event.getTypeId() == coin.SoLocation2Event.getClassTypeId():
                if self._pos:
                    pos = self._get_cursor_pos()
                    self.dist = self._distance(pos)
                    opacity = self._compute_opacity(self.dist)
                    self.update_opacity(opacity)

    def _compute_opacity(self, dist):
        if dist <= 150:
            opacity = 1
        elif 150 < dist <= 400:
            opacity = abs(1 - (dist / 300))
        else:
            opacity = 0
        return opacity
        
    def update_opacity(self, opacity):
        effects = self.overlay.graphicsEffect()
        if abs(effects.opacity() - opacity) >= 0.2:
            self.overlay.graphicsEffect().setOpacity(opacity)
            if  opacity < 0.2:
                self.overlay.graphicsEffect().setOpacity(1)
                self.clear_selection()
                self.hide()

    def show_at_cursor(self):
        self.update()
        pos = self._get_cursor_pos() + QtCore.QPoint(5, 5)
        frame_size = self.overlay.frameSize()
        self._pos = pos + QtCore.QPoint(frame_size.width() / 2, frame_size.height() / 2)
        self.overlay.move(pos)
        self.overlay.show()
        self.show()
        
    def hide(self):
        self.overlay.hide()
        if hasattr(self, 'fast_edit_overlay'):
            self.fast_edit_overlay.hide()
        self._clear_position()
        super().hide()
        
    def _clear_position(self):
        self._pos = None
        self.dist = None


class EdgeSelectionObserver:
    def __init__(self, widget):
        self.widget = widget

    def addSelection(self, doc, obj, sub, pnt):
        selection_type = None
        sub_is_edge = sub and sub.startswith('Edge')
        sub_is_face = sub and sub.startswith('Face')
        obj_is_sketch = obj and (App.ActiveDocument.getObject(obj).TypeId == 'Sketcher::SketchObject')

        if obj_is_sketch:
            selection_type = 'sketch' if sub_is_edge else None
        elif sub_is_edge:
            selection_type = 'edge' 
        elif sub_is_face:
            selection_type = 'face'

        if selection_type:
            self.widget.set_selection(doc, f'{obj}.{sub}', selection_type)
            self.widget.show_at_cursor()
        else:
            self.widget.hide()
        

    def clearSelection(self, doc):
        self.widget.hide()


if hasattr(App, "edge_overlay"):
    try:
        Gui.Selection.removeObserver(App.edge_observer)
        App.edge_overlay.deleteLater()
    except:
        pass

App.edge_overlay = EdgeToolOverlay()
App.edge_observer = EdgeSelectionObserver(App.edge_overlay)
Gui.Selection.addObserver(App.edge_observer)
