from PySide import QtWidgets, QtCore, QtGui

import FreeCAD as App
from FreeCAD import Console

from core.constants import DEFAULT_WORKBENCH, Workbenches
from core.workbench import list_wb_tools, get_wb_name


class SettingsWindow(QtWidgets.QDialog):
    def __init__(self, storage, rebuild_callback=None):
        import FreeCADGui as Gui

        super().__init__(Gui.getMainWindow())
        self.setWindowTitle("Настройки ExUI.")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        self._storage = storage
        self._storage.active_wb = Workbenches.PD
        self._storage.workbenches = self._list_workbenches()
        self._rebuild_callback = rebuild_callback
        self.init_ui()

    def _list_workbenches(self):
        import FreeCADGui as Gui

        workbenches = Gui.listWorkbenches()
        return {workbenches[name].MenuText: name for name in sorted(workbenches)}

    def init_ui(self):
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        general_gb = self._build_general_group()
        self._tool_list_wdg = self._build_tool_list_widget()
        self.menu_tools_wd = self._build_selected_tools_widget(self._tool_list_wdg)

        self._tool_list_wdg.itemChanged.connect(
            lambda item: self._on_tool_checked(item, self.menu_tools_wd)
        )

        tabs = QtGui.QTabWidget()
        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_tools_tab(), "Tools")

        left_panel_wd = QtWidgets.QWidget()
        splitter_wdg = QtWidgets.QSplitter()
        splitter_wdg.insertWidget(0, tabs)
        splitter_wdg.insertWidget(1, self.menu_tools_wd)

        left_panel_wd = QtWidgets.QWidget()
        left_panel_lyt = QtWidgets.QVBoxLayout()
        left_panel_lyt.addWidget(general_gb)
        left_panel_lyt.addWidget(splitter_wdg)
        left_panel_wd.setLayout(left_panel_lyt)

        self.layout.addWidget(left_panel_wd, alignment=QtCore.Qt.AlignTop)

        from core.workbench import list_wb_tools

        self._populate_tools_list(self._storage, self._tool_list_wdg)
        workbench = self._storage.active_wb or DEFAULT_WORKBENCH
        self.hide()
        self._check_tools(
            self._storage, workbench, self._tool_list_wdg, self.menu_tools_wd
        )
        self._build_groups_onload(self._storage, self.menu_tools_wd)

    def _build_general_tab(self):
        shape_gb = self._build_shape_group()
        position_gb = self._build_position_group()
        show_panel_wdg = self._build_show_panel_checkbox()

        general_tab_content_wdg = QtGui.QWidget()
        general_tab_content_lyt = QtWidgets.QVBoxLayout()
        general_tab_content_lyt.addWidget(shape_gb, alignment=QtCore.Qt.AlignTop)
        general_tab_content_lyt.addWidget(position_gb, alignment=QtCore.Qt.AlignTop)
        general_tab_content_lyt.addWidget(show_panel_wdg, alignment=QtCore.Qt.AlignTop)
        general_tab_content_lyt.addStretch(1)
        general_tab_content_lyt.setContentsMargins(0, 0, 0, 0)
        general_tab_content_wdg.setMaximumWidth(350)
        general_tab_content_wdg.setLayout(general_tab_content_lyt)
        return general_tab_content_wdg

    def _build_tools_tab(self):
        search_input_wdg = QtGui.QLineEdit()
        search_input_wdg.setPlaceholderText("Search")
        search_input_wdg.textChanged.connect(
            lambda text: self._autocomplete(self._storage, self._tool_list_wdg, text)
        )

        clear_btn_wdg = QtWidgets.QToolButton()
        clear_btn_wdg.setToolTip("Clear")
        clear_btn_wdg.setMaximumWidth(40)
        clear_btn_wdg.clicked.connect(search_input_wdg.clear)

        search_lyt = QtWidgets.QHBoxLayout()
        search_lyt.addWidget(search_input_wdg)
        search_lyt.addWidget(clear_btn_wdg)

        tool_list_lyt = QtWidgets.QVBoxLayout()
        tool_list_lyt.addLayout(search_lyt)
        tool_list_lyt.addWidget(self._tool_list_wdg)

        tool_container_wdg = QtWidgets.QWidget()
        tool_container_wdg.setLayout(tool_list_lyt)
        tool_container_wdg.setMinimumHeight(380)

        tools_tab_content_wdg = QtWidgets.QWidget()
        tools_tab_content_lyt = QtWidgets.QVBoxLayout()
        tools_tab_content_lyt.addStretch(1)
        tools_tab_content_wdg.setLayout(tools_tab_content_lyt)
        tools_tab_content_lyt.addWidget(tool_container_wdg)
        tools_tab_content_lyt.setContentsMargins(0, 0, 0, 0)
        tools_tab_content_wdg.setMaximumWidth(380)
        return tools_tab_content_wdg

    def _build_general_group(self):
        import FreeCADGui as Gui
        from overlay_toolbar import OverlayPosition, OverlayOrientation

        select_wb_lbl = QtGui.QLabel("Workbench")
        select_wb_lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        def on_select(storage, widget, table, idx):
            widget.hidePopup()
            storage.active_wb = storage.workbenches.get(
                widget.currentText(), DEFAULT_WORKBENCH
            )
            self._populate_tools_list(storage, self._tool_list_wdg)
            self._check_tools(
                self._storage,
                storage.active_wb,
                self._tool_list_wdg,
                self.menu_tools_wd,
            )
            self._build_groups_onload(self._storage, self.menu_tools_wd)

        select_wb_wdg = QtGui.QComboBox()
        select_wb_wdg.setMaxVisibleItems(10)
        select_wb_wdg.setStyleSheet("QComboBox { combobox-popup: 0; }")
        select_wb_wdg.blockSignals(True)
        select_wb_wdg.currentIndexChanged.connect(
            lambda idx: on_select(
                self._storage, select_wb_wdg, self._tool_list_wdg, idx
            )
        )
        select_wb_wdg.setMinimumWidth(140)
        select_wb_wdg.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        select_wb_wdg.addItems(self._storage.workbenches)

        idx = select_wb_wdg.findText(
            self._find_workbench_by_sysname(self._storage, DEFAULT_WORKBENCH)
        )
        if idx != -1:
            select_wb_wdg.setCurrentIndex(idx)
        select_wb_wdg.blockSignals(False)

        general_gb = QtGui.QGroupBox("General")
        general_gb_lyt = QtGui.QHBoxLayout()
        general_gb_lyt.addWidget(select_wb_lbl)
        general_gb_lyt.addWidget(select_wb_wdg)
        general_gb.setLayout(general_gb_lyt)
        general_gb.setMinimumWidth(300)
        return general_gb

    def _build_shape_group(self):
        shape_lbl = QtGui.QLabel("Shape")
        shape_lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        shape_wdg = QtGui.QComboBox()
        shape_wdg.blockSignals(True)
        shape_wdg.setMinimumHeight(28)
        shape_wdg.currentIndexChanged.connect(
            lambda: self._on_shape_change(shape_wdg.currentText())
        )
        shape_wdg.setMinimumWidth(140)
        shape_wdg.addItems(("Line", "Matrix"))
        shape_wdg.blockSignals(False)

        shape_lbl_wrapper = QtWidgets.QHBoxLayout()
        shape_lbl_wrapper.addWidget(shape_lbl)

        shape_wdg_wrapper = QtWidgets.QHBoxLayout()
        shape_wdg_wrapper.addWidget(shape_wdg)

        shape_lyt = QtWidgets.QHBoxLayout()
        shape_lyt.addLayout(shape_lbl_wrapper, 1)
        shape_lyt.addLayout(shape_wdg_wrapper, 1)

        shape_gb = QtGui.QGroupBox("Shape")
        shape_gb_lyt = QtWidgets.QVBoxLayout()
        shape_gb_lyt.addLayout(shape_lyt)
        shape_gb.setLayout(shape_gb_lyt)
        shape_gb.setMinimumWidth(300)
        return shape_gb

    def _build_position_group(self):
        from overlay_toolbar import OverlayPosition, OverlayOrientation

        top_pos_wdg = QtGui.QRadioButton("Top")
        top_pos_wdg.toggled.connect(
            lambda checked: self._set_pos(
                OverlayPosition.top, orientation=OverlayOrientation.horizontal
            )
        )

        bottom_pos_wdg = QtGui.QRadioButton("Bottom")
        bottom_pos_wdg.toggled.connect(
            lambda checked: self._set_pos(
                OverlayPosition.bottom, orientation=OverlayOrientation.horizontal
            )
        )
        left_pos_wdg = QtGui.QRadioButton("Left")
        left_pos_wdg.toggled.connect(
            lambda checked: self._set_pos(
                OverlayPosition.left, orientation=OverlayOrientation.vertical
            )
        )
        right_pos_wdg = QtGui.QRadioButton("Right")
        right_pos_wdg.toggled.connect(
            lambda checked: self._set_pos(
                OverlayPosition.right, orientation=OverlayOrientation.vertical
            )
        )

        position_wdg = QtWidgets.QButtonGroup()
        position_wdg.addButton(top_pos_wdg)
        position_wdg.addButton(bottom_pos_wdg)
        position_wdg.addButton(left_pos_wdg)
        position_wdg.addButton(right_pos_wdg)

        position_lyt_left = QtWidgets.QVBoxLayout()
        position_lyt_left.addWidget(top_pos_wdg)
        position_lyt_left.addWidget(bottom_pos_wdg)

        position_lyt_right = QtWidgets.QVBoxLayout()
        position_lyt_right.addWidget(left_pos_wdg)
        position_lyt_right.addWidget(right_pos_wdg)

        position_btn_lyt = QtWidgets.QHBoxLayout()
        position_btn_lyt.addLayout(position_lyt_left)
        position_btn_lyt.addLayout(position_lyt_right)
        position_btn_lyt.addStretch(1)

        position_controls_lyt = QtWidgets.QHBoxLayout()
        position_controls_lyt.addLayout(position_btn_lyt, 1)

        position_gb = QtGui.QGroupBox("Position")
        position_gb_lyt = QtWidgets.QHBoxLayout()
        position_gb_lyt.addLayout(position_controls_lyt)
        position_gb.setLayout(position_gb_lyt)
        return position_gb

    def _build_show_panel_checkbox(self):
        show_panel_wdg = QtGui.QCheckBox("Show panel")
        show_panel_wdg.setChecked(self._storage.overlay_panel_on)
        show_panel_wdg.setTristate(False)

        def toggle_show_panel(checked):
            is_panel_on = self._storage.overlay_panel_on = checked
            if not is_panel_on:
                from core.panel import destroy_overlay_panel

                destroy_overlay_panel()
            elif is_panel_on:
                from core.panel import setup_overlay_panel

                setup_overlay_panel(None)

        show_panel_wdg.toggled.connect(toggle_show_panel)
        return show_panel_wdg

    def _set_pos(self, position, orientation):
        self._storage.position = position
        self._storage.orientation = orientation
        if self._rebuild_callback:
            self._rebuild_callback()

    def _build_tool_list_widget(self):
        tool_list_wdg = QtGui.QTableWidget()
        tool_list_wdg.setColumnCount(3)
        tool_list_wdg.sortItems(1, QtCore.Qt.AscendingOrder)
        tool_list_wdg.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        tool_list_wdg.verticalHeader().setVisible(False)
        tool_list_wdg.setHorizontalHeaderLabels(("...", "Tools", "Workbench"))

        tool_list_wdg.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.Fixed
        )
        tool_list_wdg.setColumnWidth(0, 20)
        tool_list_wdg.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.Stretch
        )
        tool_list_wdg.horizontalHeader().setSectionResizeMode(
            2, QtWidgets.QHeaderView.Fixed
        )
        tool_list_wdg.setColumnWidth(2, 140)
        tool_list_wdg.horizontalHeader().setStretchLastSection(False)
        tool_list_wdg.horizontalHeader().setSortIndicatorShown(True)
        tool_list_wdg.horizontalHeader().setSortIndicator(1, QtCore.Qt.AscendingOrder)
        tool_list_wdg.horizontalHeader().setSectionsClickable(True)
        tool_list_wdg.horizontalHeader().setSectionsMovable(False)
        return tool_list_wdg

    def _build_selected_tools_widget(self, table):
        from widgets import DnDTreeWidget

        menu_tools_wd = DnDTreeWidget()
        menu_tools_wd.setColumnCount(2)
        menu_tools_wd.setHeaderLabels(["Hotkey", "Tools"])
        menu_tools_wd.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        menu_tools_wd.headerItem().setTextAlignment(
            0, QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )
        menu_tools_wd.headerItem().setTextAlignment(
            1, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        menu_tools_wd.header().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        menu_tools_wd.setColumnWidth(0, 60)
        menu_tools_wd.header().setMinimumSectionSize(60)
        menu_tools_wd.header().setStretchLastSection(True)
        menu_tools_wd.setMinimumWidth(380)
        menu_tools_wd.setRootIsDecorated(False)
        menu_tools_wd.setItemsExpandable(False)
        menu_tools_wd.on_parent_changed.connect(
            lambda items, parent: self._update_children(items, parent)
        )
        menu_tools_wd.setSelectionBehavior(QtGui.QTreeWidget.SelectRows)
        menu_tools_wd.setSelectionMode(QtGui.QTreeWidget.ExtendedSelection)

        palette = table.palette()
        grid_color = palette.color(QtGui.QPalette.Mid).name()
        base_color = palette.color(QtGui.QPalette.Base).name()
        alternate_color = palette.color(QtGui.QPalette.AlternateBase).name()
        highlight_color = palette.color(QtGui.QPalette.Highlight).name()
        highlighted_text = palette.color(QtGui.QPalette.HighlightedText).name()

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
            QTreeWidget:focus {{
                outline: none;
            }}
            QTreeWidget::item:focus {{
                outline: none;
            }}
        """)
        return menu_tools_wd

    def save_and_close(self):
        App.Console.PrintMessage("Настройки сохранены!\n")
        self.accept()

    def _push_tool(self, value: dict):
        tools = self._storage.tools.copy()
        index = self._storage.index.copy()
        workbench = self._storage.active_wb
        action_name = value["action_name"]
        if workbench in index:
            if action_name not in index[workbench]:
                tools[workbench][action_name] = value
                index[workbench].append(action_name)
        else:
            index[workbench] = [action_name]
            tools[workbench] = {action_name: value}
        self._storage.tools = tools
        self._storage.index = index

    def _remove_tool(self, action_name: str):
        workbench = self._storage.active_wb
        tools = self._storage.tools
        tools_ = tools.copy()
        index = self._storage.index.copy()
        if workbench in index:
            for idx, tool in tools[workbench].items():
                if tool["action_name"] == action_name:
                    tools_[workbench].pop(action_name)
                    index[workbench].remove(action_name)
                    break
            if not tools_[workbench]:
                tools_.pop(workbench, None)
                index.pop(workbench, None)
            self._storage.tools = tools_
            self._storage.index = index

    def _on_tool_checked(self, item, menu_tools):
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
                            action_name = item_.data(QtCore.Qt.UserRole).get(
                                "action_name"
                            )
                            self._push_tool(
                                {"pub_name": pub_name, "action_name": action_name}
                            )
                            icon = row_item.icon()
                            if icon:
                                tool_item.setIcon(column_idx, icon)
                            item.setData(
                                QtCore.Qt.UserRole, {"action_name": action_name}
                            )
                            tool_item.setData(
                                column_idx,
                                QtCore.Qt.UserRole,
                                {"action_name": action_name},
                            )
                    tool_item.setText(column_idx, value)
                menu_tools.insertTopLevelItem(row_num, tool_item)
            else:
                item_ = tools_table.item(item.row(), 1)
                value = item_.text()
                to_delete = []
                for row in range(menu_tools.topLevelItemCount()):
                    item = menu_tools.topLevelItem(row)
                    if item.text(1) == value:
                        to_delete.append(row)
                        data = item.data(1, QtCore.Qt.UserRole)
                        if data:
                            action = item.data(1, QtCore.Qt.UserRole).get("action_name")
                            self._remove_tool(action)
                        break
                for row in to_delete:
                    menu_tools.takeTopLevelItem(row)
            tools_table.blockSignals(False)
            if self._rebuild_callback:
                self._rebuild_callback()

    def _find_workbench_by_sysname(self, storage, sys_name: str) -> str:
        for idx, item in enumerate(storage.workbenches.items()):
            name, sys_name_ = item
            if sys_name_ == sys_name:
                return name
        return ""

    def _on_shape_change(self, value):
        self._storage.shape = value
        if self._rebuild_callback:
            self._rebuild_callback()

    def _populate_tools_list(self, storage: "Storage", table_widget):
        from widgets import DnDTreeWidget

        table_widget.blockSignals(True)
        table_widget.clearContents()
        table_widget.setRowCount(0)

        tools = list_wb_tools(storage, storage.active_wb or DEFAULT_WORKBENCH)

        for row, tool_name in enumerate(tools):
            table_widget.insertRow(row)

            checkbox_item = QtGui.QTableWidgetItem()
            checkbox_item.setCheckState(QtCore.Qt.Unchecked)
            checkbox_item.setFlags(
                QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled
            )
            checkbox_item.setTextAlignment(QtCore.Qt.AlignCenter)
            table_widget.setItem(row, 0, checkbox_item)

            tool = tools[tool_name]
            tool_item = QtWidgets.QTableWidgetItem(tool.text().replace("&", ""))
            tool_item.setData(QtCore.Qt.UserRole, {"action_name": tool_name})
            tool_item.setIcon(tool.icon())
            tool_item.setFlags(QtCore.Qt.ItemIsEnabled)
            tool_item.setToolTip(tool.toolTip())
            table_widget.setItem(row, 1, tool_item)

            workbench = get_wb_name(tool_name)
            if workbench:
                workbench = "FreeCAD" if workbench == "Std" else workbench
                item = QtGui.QTableWidgetItem(workbench)
                item.setFlags(QtCore.Qt.ItemIsEnabled)
                table_widget.setItem(row, 2, item)
            else:
                item = QtGui.QTableWidgetItem(tool_name)
                item.setFlags(QtCore.Qt.ItemIsEnabled)
                table_widget.setItem(row, 2, item)
        table_widget.blockSignals(False)

    def _check_tools(self, storage, workbench, tool_list, menu_tools):
        menu_tools.blockSignals(True)
        menu_tools.clear()
        tool_list.blockSignals(False)

        def _set_checked(tools, tool_list):
            for tool in tools.values():
                items = tool_list.findItems(tool["pub_name"], QtCore.Qt.MatchExactly)
                if items:
                    row = items[0].row()
                    if row is not None:
                        checkbox = tool_list.item(row, 0)
                        checkbox.setCheckState(QtCore.Qt.Checked)
                if children := tool.get("children", {}):
                    _set_checked(children, tool_list)

        if tools := storage.tools.get(workbench, {}):
            _set_checked(tools, tool_list)

    def _build_groups_onload(self, storage, menu_tools):
        def search(text, item, column, depth=1):
            if not item:
                return
            if item.text(column) == text:
                return item
            elif depth > 1:
                for idx in range(item.childCount()):
                    res = search(text, item.child(idx), column)
                    if res:
                        return res

        def get_item_by_text(tree, text, column, depth=1):
            for idx in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(idx)
                item = search(text, item, column, depth=depth)
                if item:
                    return item

        tools = storage.tools.get(storage.active_wb, {})
        menu_tools.blockSignals(True)
        for action_name, tool_data in tools.items():
            parent = None
            if "children" in tool_data:
                parent = get_item_by_text(menu_tools, tool_data["pub_name"], 1)
                if parent:
                    for tool in tool_data["children"].values():
                        child = get_item_by_text(menu_tools, tool["pub_name"], 1, 2)
                        menu_tools.takeTopLevelItem(
                            menu_tools.indexOfTopLevelItem(child)
                        )
                        parent.addChild(child)
                    parent.setExpanded(True)
        menu_tools.blockSignals(False)

    def _autocomplete(self, storage, search_table, term: str, exact_match=False):
        term = term.lower()
        if not hasattr(search_table, "_hidden_rows"):
            setattr(search_table, "_hidden_rows", set())

        def hide_row(table, row):
            if 0 <= row < table.rowCount():
                table.setRowHidden(row, True)
                table._hidden_rows.add(row)

        def show_row(table, row):
            if row in table._hidden_rows:
                if 0 <= row < table.rowCount():
                    table.setRowHidden(row, False)
                    table._hidden_rows.remove(row)

        def hide_all(table):
            for row in range(table.rowCount()):
                hide_row(table, row)

        def show_all(table):
            if table._hidden_rows:
                for row in range(table.rowCount()):
                    show_row(table, row)

        hits = 0
        rows = []
        for row in range(search_table.rowCount()):
            if item := search_table.item(row, 1):
                cell_value = item.text().lower()
                cond = cell_value == term if exact_match else term in cell_value
                if cond:
                    rows.append(row)
                    hits += 1

        if term != "" and hits == 0:
            hide_all(search_table)
        elif term == "":
            show_all(search_table)
        elif rows:
            hide_all(search_table)
            for row in rows:
                show_row(search_table, row)

    def _update_children(self, items, parent):
        from widgets import DnDTreeWidget

        tools = self._storage.tools.copy()
        workbench = self._storage.active_wb
        parent_data = None

        if parent:
            parent_action_name = parent.data(1, QtCore.Qt.UserRole).get("action_name")
            parent_data = tools[workbench].get(parent_action_name, None)

        for item, old_parent in items:
            item_action_name = item.data(1, QtCore.Qt.UserRole).get("action_name")
            if parent_data:
                if "children" not in parent_data:
                    parent_data["children"] = {}
                if tool := tools[workbench].pop(item_action_name, None):
                    parent_data["children"].update({item_action_name: tool})
            if old_parent:
                old_action_name = old_parent.data(1, QtCore.Qt.UserRole).get(
                    "action_name"
                )
                try:
                    action = tools[workbench][old_action_name]["children"].pop(
                        item_action_name, None
                    )
                    if action:
                        tools[workbench][item_action_name] = action
                except ValueError:
                    App.Console.PrintMessage(
                        f"No <{item_action_name}> in <{old_action_name}> children list."
                    )
        if parent_data:
            tools[workbench][parent_action_name] = parent_data
        self._storage.tools = tools
        if self._rebuild_callback:
            self._rebuild_callback()
