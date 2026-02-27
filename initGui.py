import copy
import json
from dataclasses import dataclass
from unittest.result import failfast

import FreeCAD as App
import FreeCADGui as Gui
from FreeCAD import Console, Units

from pivy import coin
from PySide import QtWidgets, QtCore, QtGui

PARAM_PATH = "User parameter:BaseApp/OverlayToolbar"
DEFAULT_WORKBENCH = 'PartDesignWorkbench'
translate = App.Qt.translate


@dataclass
class Workbenches:
    Arch: str = 'BIMWorkbench',
    FEM: str = 'FemWorkbench',
    SheetMetal: str = 'SMWorkbench',
    Asm4: str = 'Assembly4Workbench',
    a2p: str = 'A2plusWorkbench',
    Materials: str = 'MaterialWorkbench',
    FCGear: str = 'GearWorkbench',
    FreeCAD: str = 'Std'


class StorageField:
    def __init__(self, value=None, default=None):
        self._default = default
        
    def __set_name__(self, owner, name):
        self.name = name

    def __set__(self, instance, value):
        storage = instance._storage
        handler = self.set(storage)
        handler(self.name, value)
        print(f'Set <{self.name}>: <{value}>')
        instance.__dict__[self.name] = value

    def __get__(self, instance, owner):
        if instance is None:
            return self
        storage = instance._storage
        handler = self.get(storage)
        value = handler(self.name, self._default)
        print(f'Get <{self.name}>: <{value}>')
        return value

    def get(self, storage):
        raise NotImplementedError('<get handler> method is not implemented.')

    def set(self, storage):
        raise NotImplementedError('<set handler> method is not implemented.')


class BooleanField(StorageField):
    def get(self, storage):
        return storage.GetBool

    def set(self, storage):
        return storage.SetBool


class IntegerField(StorageField):
    def get(self, storage):
        return storage.GetInt

    def set(self, storage):
        return storage.SetInt


class FloatField(StorageField):
    def get(self, storage):
        return storage.GetFloat

    def set(self, storage):
        return storage.SetFloat


class StringField(StorageField):
    def get(self, storage):
        return storage.GetString

    def set(self, storage):
        return storage.SetString


class StringListField(StringField):
    def __set__(self, instance, value: list | tuple):
        value = ','.join(value)
        super().__set__(instance, value)
        return value

    def __get__(self, instance, owner):
        value = super().__get__(instance, owner)
        value = value.split(',')
        return value

class JsonField(StringField):
    def __set__(self, instance, value: list | tuple):
        value = json.dumps(value)
        super().__set__(instance, value)
        return value

    def __get__(self, instance, owner):
        value = super().__get__(instance, owner)
        value = json.loads(value)
        return value
    

class Storage:
    shape = StringField(default='line')
    tools = JsonField(default='{}')

    def __init__(self, storage):
        self._storage = storage
        self.active_wb = None

        self.checked_tools = None
        self.workbenches = None
        self.wbtools = {}


class SettingsWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__(Gui.getMainWindow())
        self.setWindowTitle("Настройки макроса")
        
        # Загружаем сохраненные параметры из FreeCAD
        self.setMinimumSize(800, 600)
        self.setModal(True)
        config = App.ParamGet(PARAM_PATH)
        self._storage = Storage(config)
        self._storage.workbenches = list_workbenches()
        self.init_ui()

    def init_ui(self):
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        # General settings group
        select_wb_lbl = QtGui.QLabel('Workbench')
        select_wb_lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        def on_select(storage, widget, table, idx,):
            Console.PrintMessage('Hello from combo box item.\n')
            widget.hidePopup()
            storage.active_wb = storage.workbenches.get(widget.currentText(), DEFAULT_WORKBENCH)
            # self.params.setString('ActiveWorkbench', '')
            populate_tools_list(storage, self._tool_list_wdg)
            populate_panel_tools(storage, self._storage.active_wb, self.menu_tools_wd)

        select_wb_wdg = QtGui.QComboBox()
        select_wb_wdg.setMaxVisibleItems(10)
        select_wb_wdg.setStyleSheet("QComboBox { combobox-popup: 0; }")
        
        select_wb_wdg.blockSignals(True)
        select_wb_wdg.currentIndexChanged.connect(lambda idx: on_select(self._storage, select_wb_wdg, self._tool_list_wdg, idx))
        select_wb_wdg.setMinimumWidth(140)
        select_wb_wdg.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        select_wb_wdg.addItems(self._storage.workbenches)
        idx = select_wb_wdg.findText(find_workbench_by_sysname(self._storage, DEFAULT_WORKBENCH))
        if idx != -1:
            select_wb_wdg.setCurrentIndex(idx)
        select_wb_wdg.blockSignals(False)
        general_gb = QtGui.QGroupBox('General')
        general_gb_lyt = QtGui.QHBoxLayout()
        general_gb_lyt.addWidget(select_wb_lbl)
        general_gb_lyt.addWidget(select_wb_wdg)
        general_gb.setLayout(general_gb_lyt)
        general_gb.setMinimumWidth(300)
        

        # Shape settings group

        shape_lbl = QtGui.QLabel('Shape')
        shape_lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        shape_wdg = QtGui.QComboBox()
        shape_wdg.blockSignals(True)
        shape_wdg.setMinimumHeight(28)
        shape_wdg.currentIndexChanged.connect(lambda: on_shape_change(self, shape_wdg.currentText()))
        shape_wdg.setMinimumWidth(140)
        shape_wdg.addItems((
            'Line',
            'Matrix',
        ))
        shape_wdg.blockSignals(False)

        shape_lbl_wrapper = QtGui.QHBoxLayout()
        shape_lbl_wrapper.addWidget(shape_lbl)

        shape_wdg_wrapper = QtGui.QHBoxLayout()
        shape_wdg_wrapper.addWidget(shape_wdg)

        shape_lyt = QtGui.QHBoxLayout()
        shape_lyt.addLayout(shape_lbl_wrapper, 1)
        shape_lyt.addLayout(shape_wdg_wrapper, 1)

        # size_btn_lbl = QtGui.QLabel('Icon size')
        # size_btn_lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # size_btn = QtGui.QSpinBox()
        # size_btn.setMaximum(120)
        # size_btn.setMinimum(16)
        # # size_btn.setMinimumWidth(160)
        # # size_btn.valueChanged.connect(onsize_btn)

        # size_lbl_wrapper = QtGui.QHBoxLayout()
        # size_lbl_wrapper.addWidget(size_btn_lbl)

        # size_btn_wrapper = QtGui.QHBoxLayout()
        # size_btn_wrapper.addWidget(size_btn)

        # size_btn_lyt = QtGui.QHBoxLayout()
        # size_btn_lyt.addLayout(size_lbl_wrapper, 1)
        # size_btn_lyt.addLayout(size_btn_wrapper, 1)

        # spacing_lbl = QtGui.QLabel('Icon spacing')
        # spacing_lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # spacing_wdg = QtGui.QSpinBox()
        # spacing_wdg.setMaximum(200)
        # spacing_wdg.setMinimumWidth(0)
        # # # spacing_wdg.valueChanged.connect(onIconSpacing)

        # spacing_lbl_wrapper = QtGui.QHBoxLayout()
        # spacing_lbl_wrapper.addWidget(spacing_lbl)

        # spacing_wdg_lyt = QtGui.QHBoxLayout()
        # spacing_wdg_lyt.addWidget(spacing_wdg)

        # spacing_lyt = QtGui.QHBoxLayout()
        # spacing_lyt.addLayout(spacing_lbl_wrapper, 1)
        # spacing_lyt.addLayout(spacing_wdg_lyt, 1)

        shape_gb = QtGui.QGroupBox('Shape')
        shape_gb_lyt = QtGui.QVBoxLayout()
        shape_gb_lyt.addLayout(shape_lyt)
        # shape_gb_lyt.addLayout(size_btn_lyt)
        # shape_gb_lyt.addLayout(spacing_lyt)
        shape_gb.setLayout(shape_gb_lyt)
        shape_gb.setMinimumWidth(300)
        # shape_gb_lyt.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

        # Trugger settings group
        onselect_mode_wdg = QtGui.QRadioButton('On select')
        onselect_mode_wdg.toggled.connect(
            lambda checked, data='onselect': Console.PrintMessage(f'Trigger mode is: {data}.\n')
        )

        onhotkey_mode_wdg = QtGui.QRadioButton('On hotkey')
        onhotkey_mode_wdg.toggled.connect(
            lambda checked, data='onhotkey':  Console.PrintMessage(f'Trigger mode is: {data}.\n')
        )

        trigger_mode_wdg = QtGui.QButtonGroup()
        trigger_mode_wdg.addButton(onselect_mode_wdg)
        trigger_mode_wdg.addButton(onhotkey_mode_wdg)

        trigger_mode_lyt = QtGui.QVBoxLayout()
        trigger_mode_lyt.addWidget(onselect_mode_wdg)
        trigger_mode_lyt.addWidget(onhotkey_mode_wdg)

        fading_distance_lbl = QtGui.QLabel('Fading distance')
        fading_distance_lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        fading_distance_wdg = QtGui.QSpinBox()
        fading_distance_wdg.setMaximum(999)
        fading_distance_wdg.setMinimumWidth(90)
        # # fading_distance_wdg.valueChanged.connect(onfading_distance_wdg)

        trigger_btn_lyt = QtGui.QHBoxLayout()
        trigger_btn_lyt.addLayout(trigger_mode_lyt)
        trigger_btn_lyt.addStretch(1)
        trigger_values_lyt = QtGui.QHBoxLayout()
        trigger_values_lyt.addWidget(fading_distance_lbl)
        trigger_values_lyt.addStretch(1)
        trigger_values_lyt.addWidget(fading_distance_wdg)

        trigger_controls_lyt = QtGui.QHBoxLayout()
        trigger_controls_lyt.addLayout(trigger_btn_lyt, 1)
        trigger_controls_lyt.addLayout(trigger_values_lyt, 1)
        
        trigger_gb = QtGui.QGroupBox('Trigger')
        trigger_gb_lyt = QtGui.QHBoxLayout()
        trigger_gb_lyt.addLayout(trigger_controls_lyt)
        trigger_gb.setLayout(trigger_gb_lyt)
        # trigger_gb_lyt.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

        # Shortcut settings group
        shortcuts_gb = QtGui.QGroupBox('Shortcuts')
        shortcuts_gb_lyt = QtGui.QHBoxLayout()
        # shortcuts_gb_lyt.addWidget(select_wb_wdg)
        shortcuts_gb.setLayout(shortcuts_gb_lyt)
        # shortcuts_gb_lyt.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        
        # General Tab content
        general_tab_content_wdg = QtGui.QWidget()
        general_tab_content_lyt = QtGui.QVBoxLayout()
        general_tab_content_lyt.addWidget(shape_gb, alignment=QtCore.Qt.AlignTop)
        general_tab_content_lyt.addWidget(trigger_gb, alignment=QtCore.Qt.AlignTop)
        general_tab_content_lyt.addWidget(shortcuts_gb, alignment=QtCore.Qt.AlignTop)
        general_tab_content_lyt.addStretch(1)
        general_tab_content_lyt.setContentsMargins(0, 0, 0, 0)
        general_tab_content_wdg.setMaximumWidth(350)
        general_tab_content_wdg.setLayout(general_tab_content_lyt)
        
        # Tools Tab Content
        
        search_input_wdg = QtGui.QLineEdit()
        search_input_wdg.setPlaceholderText('Search')
        # search_input_wdg.textChanged.connect(searchInToolList)

        clear_btn_wdg = QtGui.QToolButton()
        clear_btn_wdg.setToolTip('Clear')
        clear_btn_wdg.setMaximumWidth(40)
        # clear_btn_wdg.setIcon(QtGui.QIcon.fromTheme(iconBackspace))
        clear_btn_wdg.clicked.connect(search_input_wdg.clear)

        search_lyt = QtGui.QHBoxLayout()
        search_lyt.addWidget(search_input_wdg)
        search_lyt.addWidget(clear_btn_wdg)

        self._tool_list_wdg = QtGui.QTableWidget()
        self._tool_list_wdg.setColumnCount(3)
        self._tool_list_wdg.sortItems(1, QtCore.Qt.AscendingOrder)
        self._tool_list_wdg.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._tool_list_wdg.verticalHeader().setVisible(False)
        self._tool_list_wdg.setHorizontalHeaderLabels(('...', 'Tools', 'Workbench'))

        self._tool_list_wdg.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self._tool_list_wdg.setColumnWidth(0, 20)
        self._tool_list_wdg.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self._tool_list_wdg.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self._tool_list_wdg.setColumnWidth(2, 140)
        self._tool_list_wdg.horizontalHeader().setStretchLastSection(False)

        self._tool_list_wdg.horizontalHeader().setSortIndicatorShown(True)
        self._tool_list_wdg.horizontalHeader().setSortIndicator(1, QtCore.Qt.AscendingOrder)
        self._tool_list_wdg.horizontalHeader().setSectionsClickable(True)
        self._tool_list_wdg.horizontalHeader().setSectionsMovable(False)
        # self._tool_list_wdg.horizontalHeader().sectionClicked.connect(sortToolListByColumn)


        tool_list_lyt = QtGui.QVBoxLayout()
        tool_list_lyt.addLayout(search_lyt)
        tool_list_lyt.addWidget(self._tool_list_wdg)

        tool_container_wdg = QtGui.QWidget()
        tool_container_wdg.setLayout(tool_list_lyt)
        tool_container_wdg.setMinimumHeight(380)        

        tools_tab_content_wdg = QtGui.QWidget()
        tools_tab_content_lyt = QtGui.QVBoxLayout()
        # tools_tab_content_lyt.addWidget(shape_gb, alignment=QtCore.Qt.AlignTop)
        tools_tab_content_lyt.addStretch(1)
        tools_tab_content_wdg.setLayout(tools_tab_content_lyt)
        tools_tab_content_lyt.addWidget(tool_container_wdg)
        tools_tab_content_lyt.setContentsMargins(0, 0, 0, 0)
        tools_tab_content_wdg.setMaximumWidth(380)

        # Selected tools list
        self.menu_tools_wd = QtGui.QTableWidget()
        self.menu_tools_wd.setColumnCount(2)
        self.menu_tools_wd.setHorizontalHeaderLabels(['Hotkey', 'Tools'])
        self.menu_tools_wd.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.menu_tools_wd.verticalHeader().setVisible(False)
        self.menu_tools_wd.horizontalHeaderItem(0).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.menu_tools_wd.horizontalHeaderItem(1).setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.menu_tools_wd.horizontalHeader().setSectionResizeMode(QtGui.QHeaderView.Interactive)
        self.menu_tools_wd.setColumnWidth(0, 60)
        self.menu_tools_wd.horizontalHeader().setMinimumSectionSize(60)
        self.menu_tools_wd.horizontalHeader().setStretchLastSection(True)
        self.menu_tools_wd.setMinimumWidth(380)
        self._tool_list_wdg.itemChanged.connect(lambda item: onchek_tool_list(self, item, self.menu_tools_wd))

        # Tabs Constructor
        tabs = QtGui.QTabWidget()
        tabs.addTab(general_tab_content_wdg, 'General')
        tabs.addTab(tools_tab_content_wdg, 'Tools')

        left_panel_wd = QtGui.QWidget()        
        splitter_wdg = QtGui.QSplitter()
        splitter_wdg.insertWidget(0, tabs)
        splitter_wdg.insertWidget(1, self.menu_tools_wd)

        left_panel_wd = QtGui.QWidget()
        left_panel_lyt = QtGui.QVBoxLayout()
        left_panel_lyt.addWidget(general_gb)
        left_panel_lyt.addWidget(splitter_wdg)
        left_panel_wd.setLayout(left_panel_lyt)

        self.layout.addWidget(left_panel_wd, alignment=QtCore.Qt.AlignTop)
        # self.layout.addWidget(splitter_wdg, alignment=(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop))
        populate_tools_list(self._storage, self._tool_list_wdg)
        workbench = self._storage.active_wb or DEFAULT_WORKBENCH
        populate_panel_tools(self._storage, workbench, self.menu_tools_wd)
        self.hide()

    def save_and_close(self):
        # Сохраняем значения в реестр FreeCAD
        self.params.SetInt("TriggerDistance", self.dist_input.value())
        self.params.SetBool("AutoHide", self.auto_hide.isChecked())
        
        App.Console.PrintMessage("Настройки сохранены!\n")
        self.accept()


def action_callback():
    Console.PrintMessage('Hello from menubar option.\n')

class Menu:
    '''
    Builds top level menu member.

    With this class you can add
    your own item to top level menubar.
    
    | File | Edit | ... | <your menu item here> |
    
    :param items: 
        {
            <menu action name: str> : <action handler: callable>
        }
    '''
    
    def __init__(self, name: str, items: dict):
        self.name = name
        self.action_name = f'{self.name}Menu'
        self.window = Gui.getMainWindow()
        self.timer = self._make_timer()
        self._items = items 
        self._init_menu()
        
    def _trigger_action(self, callback):
        '''Action handler.'''
        callback()


    def _make_timer(self, period: int = 500):
        '''Auxiliary time constructor.
        '''

        timer = QtCore.QTimer()
        timer.timeout.connect(self._init_menu)
        timer.start(period)
        return timer

    def _init_menu(self):
        '''
        Actual Menu constructor.
        
        Builds Menu and preliminary checks.
        '''

        if self.window.property('eventLoop'):
            is_started = False
            try:
                self.window.mainWindowClosed
                self.window.workbenchActivated
                is_started = True
            except AttributeError:
                pass
            if is_started:
                self.timer.stop()
                self.timer.deleteLater()
                self._build_menu(self.name)

    def _build_action(self, name, callback):
        '''
        Builds sub action for top-level menu action.
        
        :param callback: Описание
        :param name: Описание
        '''
        option_action = QtGui.QAction(self.window)
        option_action.setText(translate(self.action_name, f'{name} settings'))
        option_action.setObjectName(name)
        option_action.triggered.connect(callback)
        return option_action
        
    def _build_menu(self, name: str) -> None:
        '''
        Builds top-level action for menubar with sub actions.

        :param name: Описание
        :type name: str
        '''

        self.window = Gui.getMainWindow()

        action = self.window.findChild(QtGui.QAction, self.action_name)
        menu = action.menu()

        for action_name, action_callback in self._items.items():
            option_action = self._build_action(action_name, lambda: self._trigger_action(action_callback))

            if action:
                menu.addAction(option_action)
            else:
                menubar = self.window.menuBar()

                action = QtGui.QAction(self.window)
                action.setObjectName(self.action_name)
                action.setIconText(translate('FreeCAD Menu', self.name))

                menu = QtGui.QMenu()
                action.setMenu(menu)
                menu.addAction(option_action)

                def add_action():
                    menubar.addAction(action)
                    action.setVisible(True)

                add_action()
                self.window.workbenchActivated.connect(add_action)            


def find_workbench_by_sysname(storage, sys_name: str) -> str:
    for idx, item in enumerate(storage.workbenches.items()):
        name, sys_name_ = item
        if sys_name_ == sys_name:
            return name
    return ''


def list_workbenches() -> dict:
    ''' Return a sorted list of workbenches for combobox '''

    workbenches = Gui.listWorkbenches()
    workbenches = {workbenches[name].MenuText: name for name in sorted(workbenches)}
    return workbenches


def list_wb_tools(storage: Storage, wb_name: str) -> dict:
    actions: dict = storage.wbtools.get(wb_name, {})
    print('TOOLS: ', list(storage.wbtools.keys()))
    if actions:
        return actions

    exclude = (
        'File',
        'Edit',
        # 'Workbench',
        # 'Macro',
        'Help',
        # 'FreeCAD',
        'Std',
        'Clipboard',
    )
    window = Gui.getMainWindow()
    original_wb = Gui.activeWorkbench().name()
    Gui.activateWorkbench(wb_name)
    wb = Gui.activeWorkbench() 
    toolbars = wb.getToolbarItems()
    toolbars = {k: v for k, v in toolbars.items() if k not in exclude}.items()
    for tb_name, tools in toolbars:

        for name in tools:
            if get_wb_name(name) in exclude:
                continue
            tool = window.findChild(QtGui.QAction, name)
            if tool and tool.icon():
                actions[name] = tool

    Gui.activateWorkbench(original_wb)
    storage.wbtools[wb_name] = actions
    return actions
    

# def list_tools():
#     tools = {}
#     window = Gui.getMainWindow()
#     part_wb = window.findChild(QtGui.QAction, 'Std_Workbench')
#     parent = part_wb.parent()
#     group = parent.findChild(QtGui.QActionGroup)

#     for action in group.actions():
#         if action.objectName() != '' and action.icon():
#             tools[action.objectName()] = action

#     for action in window.findChildren(QtGui.QAction):
#         not_in_tools = (
#             action.objectName() not in (None, '') 
#             and not (action.objectName() in tools) 
#             and action.icon()
#         )
#         if not_in_tools:
#             tools[action.objectName()] = action
#     return tools


# def list_tools_by_wb(wb_name):
#     tools = {}
#     window = Gui.getMainWindow()
#     part_wb = window.findChild(QtGui.QAction, 'Std_Workbench')
#     parent = part_wb.parent()
#     group = parent.findChild(QtGui.QActionGroup)

#     for action in group.actions():
#         if action.objectName() != '' and action.icon():
#             tools[action.objectName()] = action

#     for action in window.findChildren(QtGui.QAction):
#         name = action.objectName()
#         not_in_tools = (
#             name not in (None, '') 
#             and not (name in tools) 
#             and action.icon()
#         )
#         print(name)
#         if not_in_tools and name.startswith(wb_name):
#             tools[name] = action
#     return tools


def get_wb_name(command: QtGui.QAction) -> str:
    ''' Get the workbench name from tool.'''

    parts = command.split('_')
    name = parts[0]

    return name if name else 'None'


def populate_tools_list(storage: Storage, table_widget):
    # row = 0
    tools = list_wb_tools(storage, storage.active_wb or DEFAULT_WORKBENCH)

    table_widget.blockSignals(True)
    table_widget.clearContents()
    table_widget.setRowCount(0)

    for row, tool_name in enumerate(tools):
        table_widget.insertRow(row)

        # Column 0: id
        checkbox_item = QtGui.QTableWidgetItem()
        checkbox_item.setCheckState(QtCore.Qt.Unchecked)
        checkbox_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        checkbox_item.setTextAlignment(QtCore.Qt.AlignCenter)
        table_widget.setItem(row, 0, checkbox_item)

        # Column 1: tool icon
        tool = tools[tool_name]
        tool_item = QtWidgets.QTableWidgetItem(tool.text().replace('&', ''))
        tool_item.setData(QtCore.Qt.UserRole, tool_name)
        tool_item.setIcon(tool.icon())
        tool_item.setFlags(QtCore.Qt.ItemIsEnabled)
        tool_item.setToolTip(tool.toolTip())
        table_widget.setItem(row, 1, tool_item)

        # Column 2: Workbench name
        workbench = get_wb_name(tool_name)
        if workbench:
            workbench = 'FreeCAD' if workbench == 'Std' else workbench
            item = QtGui.QTableWidgetItem(workbench)
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            table_widget.setItem(row, 2, item)
        else:
            item = QtGui.QTableWidgetItem(tool_name)
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            table_widget.setItem(row, 2, item)
        # row += 1
    table_widget.blockSignals(False)


def populate_panel_tools(
    storage: Storage,
    workbench: str,
    menu_tools,
) -> None:
    tools = storage.tools
    tools = tools.get(workbench)

    menu_tools.blockSignals(True)
    menu_tools.clearContents()
    menu_tools.setRowCount(0)

    if not tools:
        return

    for row, tool in enumerate(tools):
        menu_tools.insertRow(row)

        shortkey = str(row + 1)
        item = QtWidgets.QTableWidgetItem(shortkey)
        menu_tools.setItem(row, 0, item)

        action_name = tool['action_name']
        value = tool['pub_name']
        item = QtWidgets.QTableWidgetItem(value)
        item.setData(QtCore.Qt.UserRole, action_name)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        if wbtools := storage.wbtools.get(workbench):
            if action := wbtools.get(action_name):
                item.setIcon(action.icon())

        menu_tools.setItem(row, 1, item)


def onchek_tool_list(self, item, menu_tools):
    def push_value(self, value):
        tools = self._storage.tools.copy()
        workbench = self._storage.active_wb

        if workbench in tools:
            tools[workbench].append(value)
            self._storage.tools = tools
        else:
            tools[workbench] = [value]
            self._storage.tools = tools

    def rm_value(self, value):
        tools = self._storage.tools.copy()
        workbench = self._storage.active_wb
        tools = self._storage.tools
        if workbench in tools:
            tools[workbench].remove(value)
    

    event_row = item.row()
    if item.column() == 0:
        tools_table = item.tableWidget()
        tools_table.blockSignals(True)
        if item.checkState() == QtCore.Qt.Checked:
            row_num = menu_tools.rowCount()
            # item.setData(QtCore.Qt.UserRole, row_num)
            menu_tools.insertRow(row_num)
            for column_idx in range(tools_table.columnCount()):
                row_item = tools_table.item(event_row, column_idx)
                
                if column_idx == 0:
                    value = str(row_num + 1)
                else:
                    value = row_item.text()
                    if column_idx == 1:
                        item_ = tools_table.item(event_row, 1)
                        pub_name = item_.text()
                        action_name = item_.data(QtCore.Qt.UserRole)
                        push_value(self, {'pub_name': pub_name, 'action_name': action_name})

                tool_item = QtWidgets.QTableWidgetItem(value)
                icon = row_item.icon()
                if icon:
                    tool_item.setIcon(icon)
                tool_item.setFlags(QtCore.Qt.ItemIsEnabled)
                # tool_item.setToolTip(tool.toolTip())
                menu_tools.setItem(row_num, column_idx, tool_item)
            tools_table.blockSignals(False)
        else:
            row_idx = item.data(QtCore.Qt.UserRole)
            menu_tools.removeRow(row_idx)
            rm_value(self, value)


def on_shape_change(self, value):
    self._storage.shape = value
    print('Shape changed')


context_toolbar_settings = SettingsWindow()
menu = Menu(name='Accessories', items={'Ext UI': context_toolbar_settings.show})

# Запуск диалога
# dlg = MacroSettings()
# if dlg.exec_() == QtWidgets.QDialog.Accepted:
#     print("Пользователь нажал OK")
