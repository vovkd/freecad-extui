def setup_extui():
    import os
    import sys
    import inspect

    import FreeCAD as App
    import FreeCADGui as Gui
    from FreeCAD import Console

    from PySide import QtWidgets, QtCore, QtGui

    import utils
    import store
    import widgets

    from overlay_toolbar import (
        OverlayPanel,
        OverlayPosition,
        OverlayOrientation,
    )

    module_dir = os.path.dirname(
        os.path.abspath(inspect.getfile(inspect.currentframe()))
    )
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
        sys.path.insert(0, utils.__file__)
        sys.path.insert(0, store.__file__)
        sys.path.insert(0, widgets.__file__)

    from store import Storage
    from widgets import DnDTreeWidget
    from utils import (
        get_tools_from_settings,
        global_exception_handler,
    )

    from core.constants import PARAM_PATH, DEFAULT_WORKBENCH, Workbenches
    from core.storage import Storage as StorageCore
    from core.workbench import list_wb_tools
    from core.panel import (
        setup_overlay_panel as core_setup_panel,
        destroy_overlay_panel as core_destroy_panel,
        rebuild_panels as core_rebuild_panels,
    )

    from core.settings import SettingsWindow
    from core.menu import Menu
    from core.events import DocumentEventsHandler

    translate = App.Qt.translate

    def action_callback():
        Console.PrintMessage("Hello from menubar option.\n")

    def find_workbench_by_sysname(storage, sys_name: str) -> str:
        for idx, item in enumerate(storage.workbenches.items()):
            name, sys_name_ = item
            if sys_name_ == sys_name:
                return name
        return ""

    def list_workbenches() -> dict:
        workbenches = Gui.listWorkbenches()
        workbenches = {workbenches[name].MenuText: name for name in sorted(workbenches)}
        return workbenches

    def get_wb_name(command: str) -> str:
        parts = command.split("_")
        name = parts[0]
        return name if name else "None"

    def populate_tools_list(storage: Storage, table_widget):
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

    def check_tools(storage, workbench, tool_list, menu_tools):
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

    def build_groups_onload(storage, menu_tools):
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

    def search(storage, term: str) -> list[str]:
        results = []
        tools = storage.wbtools[storage.active_wb]
        for name in tools:
            if term.lower() in name.lower():
                results.append(tools[name].text())

        return results

    def autocomplete(storage, search_table, term: str, exact_match=False):
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

        results = search(storage, term)

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

    def update_children(
        storage: Storage,
        items: tuple[tuple[QtWidgets.QTreeWidgetItem, QtWidgets.QTreeWidgetItem]],
        parent: QtWidgets.QTreeWidgetItem,
    ) -> None:
        tools = storage.tools.copy()
        workbench = storage.active_wb
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
        storage.tools = tools
        core_rebuild_panels()

    def on_shape_change(self, value):
        self._storage.shape = value

    def create_menu(window):
        window = Gui.getMainWindow()
        if not window:
            Console.PrintError("Main window not available yet.\n")
            return

        config = App.ParamGet(PARAM_PATH)
        storage = Storage(config)
        context_toolbar_settings = SettingsWindow(storage)
        menu = Menu(
            name="Ext UI", items={"Overlay panel": context_toolbar_settings.show}
        )

        if not hasattr(window, "extui"):
            setattr(window, "extui", dict())

        window.extui["menu"] = menu
        window.extui["panels"] = {}
        window.extui["storage"] = storage

        doc_observer = DocumentEventsHandler(App, handlers=(core_setup_panel,))
        window.extui["doc_observer"] = doc_observer
        window.workbenchActivated.connect(on_workbench_activated)

    def setup_overlay_panel(doc=None):
        if doc is None:
            doc = App.ActiveDocument
        window = Gui.getMainWindow()
        storage = window.extui["storage"]
        workbench = Gui.activeWorkbench().name()
        tools = get_tools_from_settings(
            storage,
            workbench,
            storage.tools,
        )

        if storage.overlay_panel_on and tools:
            doc_panels = window.extui["panels"].get(doc.uid, {})
            if not isinstance(doc_panels.get("overlay"), OverlayPanel):
                overlay_panel = OverlayPanel(
                    parent=window,
                    tools=tools,
                    position=storage.position,
                    orientation=storage.orientation,
                )
                window.extui["panels"].update({doc.uid: {"overlay": overlay_panel}})
                overlay_panel.show()

    def destroy_overlay_panel(doc=None):
        app = Gui.getMainWindow()
        panels = app.extui["panels"].items()
        for key, item in panels:
            panel = item.get("overlay")
            if panel:
                app.extui["panels"][key].pop("overlay")
                panel.destroy()

    def rebuild_panels():
        window = Gui.getMainWindow()
        if hasattr(window, "extui"):
            destroy_overlay_panel()
            setup_overlay_panel()

    def on_workbench_activated():
        wb = Gui.activeWorkbench()
        window = Gui.getMainWindow()
        if not hasattr(window, "extui") or "storage" not in window.extui:
            return
        storage = window.extui["storage"]
        list_wb_tools(storage, wb.name() or DEFAULT_WORKBENCH)
        rebuild_panels()

    window = Gui.getMainWindow()

    def try_create_menu():
        create_menu(window)

    QtCore.QTimer.singleShot(150, try_create_menu)

    sys.excepthook = global_exception_handler


setup_extui()
