def setup_extui():
    import os
    import sys
    import inspect
    import uuid

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

    def create_menu(window):
        window = Gui.getMainWindow()
        if not window:
            Console.PrintError("Main window not available yet.\n")
            return

        config = App.ParamGet(PARAM_PATH)
        storage = Storage(config)
        context_toolbar_settings = SettingsWindow(
            storage, rebuild_callback=rebuild_panels
        )
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
        if doc is None:
            return
        window = Gui.getMainWindow()
        storage = window.extui["storage"]

        if not hasattr(doc, "uid"):
            doc.addProperty("App::PropertyString", "uid", "CustomAttributes")
            doc.uid = str(uuid.uuid4())

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

        def check_attr(wb, name):
            if hasattr(wb, name):
                window = Gui.getMainWindow()
                storage = window.extui['storage']
                list_wb_tools(storage, wb.name() or DEFAULT_WORKBENCH)
                rebuild_panels()
 
        QtCore.QTimer.singleShot(150, lambda: check_attr(wb, '__Workbench__'))

    window = Gui.getMainWindow()

    def try_create_menu():
        create_menu(window)

    QtCore.QTimer.singleShot(150, try_create_menu)

    sys.excepthook = global_exception_handler


setup_extui()
