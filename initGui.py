from json import tool


def setup_extui():
    import os
    import sys
    import inspect
    from dataclasses import dataclass

    import FreeCAD as App
    import FreeCADGui as Gui
    from FreeCAD import Console, Units

    import store
    import widgets

    module_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
        sys.path.insert(0, store.__file__)
        sys.path.insert(0, widgets.__file__)

    from store import Storage
    from widgets import DnDTreeWidget

    from pivy import coin
    from PySide import QtWidgets, QtCore, QtGui

    PARAM_PATH = "User parameter:BaseApp/OverlayToolbar"
    DEFAULT_WORKBENCH = 'PartDesignWorkbench'
    translate = App.Qt.translate

    @dataclass
    class Workbenches:
        Arch: str = 'BIMWorkbench'
        PD: str = 'PartDesignWorkbench'
        FEM: str = 'FemWorkbench'
        SheetMetal: str = 'SMWorkbench'
        Asm4: str = 'Assembly4Workbench'
        a2p: str = 'A2plusWorkbench'
        Materials: str = 'MaterialWorkbench'
        FCGear: str = 'GearWorkbench'
        FreeCAD: str = 'Std'


    class SettingsWindow(QtWidgets.QDialog):
        def __init__(self):
            super().__init__(Gui.getMainWindow())
            self.setWindowTitle('Настройки ExUI.')
            
            # Загружаем сохраненные параметры из FreeCAD
            self.setMinimumSize(800, 600)
            self.setModal(True)
            config = App.ParamGet(PARAM_PATH)
            self._storage = Storage(config)
            self._storage.active_wb = Workbenches.PD
            self._storage.workbenches = list_workbenches()
            self.init_ui()

        def init_ui(self):
            self.layout = QtWidgets.QHBoxLayout()
            self.setLayout(self.layout)

            # General settings group
            select_wb_lbl = QtGui.QLabel('Workbench')
            select_wb_lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

            def on_select(storage, widget, table, idx,):
                widget.hidePopup()
                storage.active_wb = storage.workbenches.get(widget.currentText(), DEFAULT_WORKBENCH)
                populate_tools_list(storage, self._tool_list_wdg)
                check_tools(self._storage, storage.active_wb, self._tool_list_wdg, self.menu_tools_wd)

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

            # Trigger settings group
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
            position_gb = QtGui.QGroupBox('Position')
            position_gb_lyt = QtGui.QHBoxLayout()

            top_pos_wdg = QtGui.QRadioButton('Top')
            top_pos_wdg.toggled.connect(
                lambda checked, data='onselect': Console.PrintMessage(f'Trigger mode is: {data}.\n')
            )

            bottom_pos_wdg = QtGui.QRadioButton('Bottom')
            bottom_pos_wdg.toggled.connect(
                lambda checked, data='onhotkey':  Console.PrintMessage(f'Trigger mode is: {data}.\n')
            )
            left_pos_wdg = QtGui.QRadioButton('Left')
            left_pos_wdg.toggled.connect(
                lambda checked, data='onhotkey':  Console.PrintMessage(f'Trigger mode is: {data}.\n')
            )
            right_pos_wdg = QtGui.QRadioButton('Right')
            right_pos_wdg.toggled.connect(
                lambda checked, data='onhotkey':  Console.PrintMessage(f'Trigger mode is: {data}.\n')
            )

            position_wdg = QtGui.QButtonGroup()
            position_wdg.addButton(top_pos_wdg)
            position_wdg.addButton(bottom_pos_wdg)
            position_wdg.addButton(left_pos_wdg)
            position_wdg.addButton(right_pos_wdg)

            position_lyt_left = QtGui.QVBoxLayout()
            position_lyt_left.addWidget(top_pos_wdg)
            position_lyt_left.addWidget(bottom_pos_wdg)

            position_lyt_right = QtGui.QVBoxLayout()
            position_lyt_right.addWidget(left_pos_wdg)
            position_lyt_right.addWidget(right_pos_wdg)

            position_btn_lyt = QtGui.QHBoxLayout()
            position_btn_lyt.addLayout(position_lyt_left)
            position_btn_lyt.addLayout(position_lyt_right)
            position_btn_lyt.addStretch(1)

            position_controls_lyt = QtGui.QHBoxLayout()
            position_controls_lyt.addLayout(position_btn_lyt, 1)

            position_gb = QtGui.QGroupBox('Position')
            position_gb_lyt = QtGui.QHBoxLayout()
            position_gb_lyt.addLayout(position_controls_lyt)
            position_gb.setLayout(position_gb_lyt)
            
            # General Tab content
            general_tab_content_wdg = QtGui.QWidget()
            general_tab_content_lyt = QtGui.QVBoxLayout()
            general_tab_content_lyt.addWidget(shape_gb, alignment=QtCore.Qt.AlignTop)
            general_tab_content_lyt.addWidget(trigger_gb, alignment=QtCore.Qt.AlignTop)
            general_tab_content_lyt.addWidget(position_gb, alignment=QtCore.Qt.AlignTop)
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

            self._tool_list_wdg = self._build_tool_list_widget()

            tool_list_lyt = QtGui.QVBoxLayout()
            tool_list_lyt.addLayout(search_lyt)
            tool_list_lyt.addWidget(self._tool_list_wdg)

            tool_container_wdg = QtGui.QWidget()
            tool_container_wdg.setLayout(tool_list_lyt)
            tool_container_wdg.setMinimumHeight(380)        

            tools_tab_content_wdg = QtGui.QWidget()
            tools_tab_content_lyt = QtGui.QVBoxLayout()
            tools_tab_content_lyt.addStretch(1)
            tools_tab_content_wdg.setLayout(tools_tab_content_lyt)
            tools_tab_content_lyt.addWidget(tool_container_wdg)
            tools_tab_content_lyt.setContentsMargins(0, 0, 0, 0)
            tools_tab_content_wdg.setMaximumWidth(380)

            # Selected tools list
            self.menu_tools_wd = self._build_selected_tools_widget(self._tool_list_wdg)
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
            populate_tools_list(self._storage, self._tool_list_wdg)
            workbench = self._storage.active_wb or DEFAULT_WORKBENCH
            self.hide()
            check_tools(self._storage, workbench, self._tool_list_wdg, self.menu_tools_wd)
            build_groups_onload(self._storage, self.menu_tools_wd)
        
        def _build_tool_list_widget(self):
            tool_list_wdg = QtGui.QTableWidget()
            tool_list_wdg.setColumnCount(3)
            tool_list_wdg.sortItems(1, QtCore.Qt.AscendingOrder)
            tool_list_wdg.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            tool_list_wdg.verticalHeader().setVisible(False)
            tool_list_wdg.setHorizontalHeaderLabels(('...', 'Tools', 'Workbench'))

            tool_list_wdg.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
            tool_list_wdg.setColumnWidth(0, 20)
            tool_list_wdg.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
            tool_list_wdg.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
            tool_list_wdg.setColumnWidth(2, 140)
            tool_list_wdg.horizontalHeader().setStretchLastSection(False)

            tool_list_wdg.horizontalHeader().setSortIndicatorShown(True)
            tool_list_wdg.horizontalHeader().setSortIndicator(1, QtCore.Qt.AscendingOrder)
            tool_list_wdg.horizontalHeader().setSectionsClickable(True)
            tool_list_wdg.horizontalHeader().setSectionsMovable(False)    
            return tool_list_wdg    
        
        def _build_selected_tools_widget(self, table):
            # menu_tools_wd = QtGui.QTreeWidget()
            menu_tools_wd = DnDTreeWidget()
            menu_tools_wd.setColumnCount(2)
            menu_tools_wd.setHeaderLabels(['Hotkey', 'Tools'])
            menu_tools_wd.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            menu_tools_wd.headerItem().setTextAlignment(0, QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            menu_tools_wd.headerItem().setTextAlignment(1, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            menu_tools_wd.header().setSectionResizeMode(QtGui.QHeaderView.Interactive)
            menu_tools_wd.setColumnWidth(0, 60)
            menu_tools_wd.header().setMinimumSectionSize(60)
            menu_tools_wd.header().setStretchLastSection(True)
            menu_tools_wd.setMinimumWidth(380)
            menu_tools_wd.setRootIsDecorated(False)
            menu_tools_wd.setItemsExpandable(False)
            menu_tools_wd.on_parent_changed.connect(lambda items, parent: update_children(self._storage, items, parent))
            
            menu_tools_wd.setSelectionBehavior(QtGui.QTreeWidget.SelectRows)
            menu_tools_wd.setSelectionMode(QtGui.QTreeWidget.ExtendedSelection)

            palette = table.palette()
            grid_color = palette.color(QtGui.QPalette.Mid).name()
            base_color = palette.color(QtGui.QPalette.Base).name()
            alternate_color = palette.color(QtGui.QPalette.AlternateBase).name()
            highlight_color = palette.color(QtGui.QPalette.Highlight).name()
            highlighted_text = palette.color(QtGui.QPalette.HighlightedText).name()
            
            # === EXACT BORDER STYLING LIKE QTableWidget ===
            menu_tools_wd.setStyleSheet(f"""
                QTreeWidget {{

                    alternate-background-color: {alternate_color};
                    
                    selection-background-color: {highlight_color};
                    selection-color: {highlighted_text};

                    outline: none;
                }}
                
                QTreeWidget::item {{
                    border-right: 1px solid {grid_color};
                    border-bottom: 1px solid {grid_color};
                    padding: 2px 4px;
                }}
                
                QTreeWidget::item:selected {{
                    background-color: {highlight_color};
                    color: {highlighted_text};
                }}
                
                QTreeWidget::item:selected:!active {{
                    background-color: {palette.color(QtGui.QPalette.Inactive, QtGui.QPalette.Highlight).name()};
                }}
                
                /* Header styling exactly like QTableWidget */
                QHeaderView::section {{
                    padding: 4px;
                    border: 1px solid {grid_color};
                    border-bottom: 2px solid {grid_color};
                    font-weight: bold;
                }}
                
                QHeaderView::section:checked {{
                    background-color: {palette.color(QtGui.QPalette.Midlight).name()};
                }}
                
                QHeaderView::section:hover {{
                    background-color: {palette.color(QtGui.QPalette.Light).name()};
                }}
                
                /* Remove focus rectangle */
                QTreeWidget:focus {{
                    outline: none;
                }}
                
                QTreeWidget::item:focus {{
                    outline: none;
                }}
            """)
            return menu_tools_wd
            
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
            self._items = items 
            self._build_menu(self.name)
            
        def _trigger_action(self, callback: callable):
            '''Action handler.'''
            callback()

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

            for action_name, action_callback in self._items.items():
                option_action = self._build_action(action_name, lambda: self._trigger_action(action_callback))

                if action:
                    menu = action.menu()
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
        try:
            original_wb = Gui.activeWorkbench().name()
        except:
            original_wb = DEFAULT_WORKBENCH
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


    def get_wb_name(command: QtGui.QAction) -> str:
        ''' Get the workbench name from tool.'''

        parts = command.split('_')
        name = parts[0]

        return name if name else 'None'


    def populate_tools_list(storage: Storage, table_widget):
        table_widget.blockSignals(True)
        table_widget.clearContents()
        table_widget.setRowCount(0)

        tools = list_wb_tools(storage, storage.active_wb or DEFAULT_WORKBENCH)

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
            tool_item.setData(QtCore.Qt.UserRole, {'action_name': tool_name})
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
        table_widget.blockSignals(False)


    def check_tools(storage, workbench, tool_list, menu_tools):
        menu_tools.blockSignals(True)
        menu_tools.clear()
        tool_list.blockSignals(False)
        # storage.checked_tools = []

        for tool in storage.tools.get(workbench, []):
            name = storage.tools[workbench][tool]['pub_name']
            items = tool_list.findItems(name, QtCore.Qt.MatchExactly)
            item = items[0] if items else []
            if item:
                row = item.row()
                checkbox = tool_list.item(row, 0)
                checkbox.setCheckState(QtCore.Qt.Checked)
    
    
    def build_groups_onload(storage, menu_tools):
        
        def search(text, item, column, depth=1):
            if not item:
                return
        
            print('item 1: ', item)
            if item.text(column) == text:
                return item
            
            elif depth > 1:
                for idx in range(item.childCount()):
                    res = search(text, item.child(idx), column)
                    if res:
                        print('item 3', item)
                        return res

        def get_item_by_text(tree, text, column,  depth=1):
            for idx in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(idx)
                item = search(text, item, column, depth=depth)
                if item: 
                    return item

        tools = storage.tools.get(storage.active_wb, {})
        menu_tools.blockSignals(True)
        for action_name, tool_data in tools.items():
            parent = None
            if 'children' in tool_data:
                parent = get_item_by_text(menu_tools, tool_data['pub_name'], 1)

                if parent:
                    for action_name in tool_data['children']:
                        child_data = tools[action_name]
                        child = get_item_by_text(menu_tools, child_data['pub_name'], 1, 2)
                        menu_tools.takeTopLevelItem(menu_tools.indexOfTopLevelItem(child))
                        parent.addChild(child)
                    parent.setExpanded(True)
        menu_tools.blockSignals(False)


    def update_children(
        storage,
        items: tuple[tuple[QtWidgets.QTreeWidgetItem, QtWidgets.QTreeWidgetItem]],
        parent: QtWidgets.QTreeWidgetItem,
    ) -> None:
        print('Catched "parent changed" signal.')
        tools = storage.tools.copy()
        workbench = storage.active_wb
        parent_action_name = parent.data(1, QtCore.Qt.UserRole).get('action_name')
        parent_data = tools[workbench].get(parent_action_name, None)

        for item, old_parent in items:
            item_action_name = item.data(1, QtCore.Qt.UserRole).get('action_name')
            if parent_data:
                if 'children' not in parent_data:
                    parent_data['children'] = []
                parent_data['children'].append(item_action_name)
            if old_parent:
                old_action_name = old_parent.data(1, QtCore.Qt.UserRole).get('action_name')
                try:
                    tools[workbench][old_action_name]['children'].remove(item_action_name)    
                except ValueError:
                    print(f'No <{item_action_name}> in <{old_action_name}> children list.')
        tools[workbench][parent_action_name] = parent_data
        storage.tools = tools 

    
    def onchek_tool_list(self, item, menu_tools):
        def push_value(self, value):
            tools = self._storage.tools
            print(tools)
            workbench = self._storage.active_wb
            action_name = value['action_name']
            print(action_name)
            if workbench in tools:
                if action_name not in tools[workbench]:
                    tools[workbench][action_name] = value
                    self._storage.tools = tools.copy()
            else:
                tools[workbench] = {action_name: value}
                self._storage.tools = tools.copy()

        def rm_value(self, value):
            workbench = self._storage.active_wb
            tools = self._storage.tools
            tools_ = tools.copy()
            if workbench in tools:
                for idx, tool in tools[workbench].items():
                    action_name = tool['action_name']
                    if action_name == value:
                        tools_[workbench].pop(action_name)
                        break
                if not tools_[workbench]:
                    tools_.pop(workbench)
                self._storage.tools = tools_.copy()

        event_row = item.row()
        tools_table = item.tableWidget()
        if item.column() == 0:
            tools_table.blockSignals(True)
            if item.checkState() == QtCore.Qt.Checked:
                row_num = menu_tools.topLevelItemCount()

                tool_item = QtWidgets.QTreeWidgetItem()
                for column_idx in range(tools_table.columnCount()):
                    row_item = tools_table.item(event_row, column_idx)
                    if column_idx == 0:
                        value = str(row_num + 1)
                    else:
                        value = row_item.text()
                        if column_idx == 1:
                            item_ = tools_table.item(event_row, 1)
                            pub_name = item_.text()
                            action_name = item_.data(QtCore.Qt.UserRole).get('action_name')
                            push_value(self, {'pub_name': pub_name, 'action_name': action_name})
                            icon = row_item.icon()
                            if icon:
                                tool_item.setIcon(column_idx, icon)
                            item.setData(QtCore.Qt.UserRole, {'action_name': action_name})
                            tool_item.setData(column_idx, QtCore.Qt.UserRole, {'action_name': action_name})
                            
                    tool_item.setText(column_idx, value)
                menu_tools.insertTopLevelItem(row_num, tool_item)
            else:
                item = tools_table.item(item.row(), 1)
                value = item.text()
                to_delete = []
                for row in range(menu_tools.topLevelItemCount()):
                    item = menu_tools.topLevelItem(row)
                    if item.text(1) == value:
                        to_delete.append(row)
                        item_ = menu_tools.topLevelItem(row)
                        data = item_.data(1, QtCore.Qt.UserRole)
                        if data:
                            action = item_.data(1, QtCore.Qt.UserRole).get('action_name')
                            rm_value(self, action)
                        break
                for row in to_delete:
                    item_ = menu_tools.takeTopLevelItem(row)
            tools_table.blockSignals(False)


    def on_shape_change(self, value):
        self._storage.shape = value
        

    def create_menu(window, timer):
        App.Console.PrintMessage("Try create menu. \n")
        if window.property("eventLoop"):
            started = False
            try:
                window.mainWindowClosed
                window.workbenchActivated
                App.Console.PrintMessage("Cheked window. \n")
                started = True
                App.Console.PrintMessage("Window started. \n")
            except AttributeError:
                pass

            if started:
                timer.stop()
                timer.deleteLater()
                App.Console.PrintMessage("Stopped timer. \n")
                context_toolbar_settings = SettingsWindow()
                menu = Menu(name='Ext UI', items={'Ext UI': context_toolbar_settings.show})

    window = Gui.getMainWindow()
    timer = QtCore.QTimer()
    timer.timeout.connect(lambda: create_menu(window, timer))
    timer.start(100)

setup_extui()