# manager.py
import sys

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets, QtCore, QtGui

from store import Storage
from document_observer import DocumentEventsHandler
from workbench_utils import list_wb_tools, get_workbench_by_menu_text, DEFAULT_WORKBENCH
from utils import global_exception_handler, get_tools_from_settings
from settings_dialog import SettingsWindow
from overlay_panel import OverlayPanel
import overlay_panel as overlay_module  # for position/orientation enums


class OverlayToolbarManager:
    """Singleton manager for ExUI – controls panels, settings, and event handling."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self):
        if self._initialized:
            return
        self._initialized = True

        # Install global exception handler
        sys.excepthook = global_exception_handler

        # Get FreeCAD parameter storage
        param_path = "User parameter:BaseApp/OverlayToolbar"
        config = App.ParamGet(param_path)
        self.storage = Storage(config)

        # Prepare workbenches list
        from workbench_utils import list_workbenches
        self.storage.workbenches = list_workbenches()
        self.storage.active_wb = DEFAULT_WORKBENCH

        # Internal data
        self.panels = {}  # {doc_uid: {'overlay': OverlayPanel}}
        self.doc_observer = None
        self._menu = None
        self._settings_window = None

        # Setup menu and observers after main window is ready
        self._setup_on_startup()

    def _setup_on_startup(self):
        """Wait for main window and first workbench activation."""
        window = Gui.getMainWindow()
        if window:
            # If window already exists, setup immediately
            self._create_menu_and_observers()
        else:
            # Wait for window creation (should not happen in normal FreeCAD)
            timer = QtCore.QTimer()
            timer.timeout.connect(lambda: self._check_window_and_setup(timer))
            timer.start(100)

    def _check_window_and_setup(self, timer):
        window = Gui.getMainWindow()
        if window:
            timer.stop()
            timer.deleteLater()
            self._create_menu_and_observers()

    def _create_menu_and_observers(self):
        """Create the 'Ext UI' menu and attach document/workbench observers."""
        window = Gui.getMainWindow()
        if hasattr(window, 'extui_manager_setup_done'):
            return
        window.extui_manager_setup_done = True

        # Create menu
        self._create_menu()

        # Setup document observer with handler for overlay panel creation
        self.doc_observer = DocumentEventsHandler(App, handlers=[self.on_document_activated])
        # Connect workbench activation signal
        window.workbenchActivated.connect(self.on_workbench_activated)

        # Initial panel creation for active document
        doc = App.ActiveDocument
        if doc:
            self.on_document_activated(doc)

    def _create_menu(self):
        """Add top-level 'Ext UI' menu with 'Overlay panel settings' action."""
        window = Gui.getMainWindow()
        menu_name = 'Ext UI'
        action_name = f'{menu_name}Menu'

        # Check if already exists
        if window.findChild(QtGui.QAction, action_name):
            return

        # Create menu action
        menu_action = QtGui.QAction(window)
        menu_action.setObjectName(action_name)
        menu_action.setIconText(App.Qt.translate('FreeCAD Menu', menu_name))

        # Create submenu
        menu = QtGui.QMenu()
        menu_action.setMenu(menu)

        # Add settings action
        settings_action = QtGui.QAction(window)
        settings_action.setText('Overlay panel settings')
        settings_action.triggered.connect(self.show_settings)
        menu.addAction(settings_action)

        # Insert into menubar
        menubar = window.menuBar()
        menubar.addAction(menu_action)
        menu_action.setVisible(True)

        self._menu = menu_action

    def show_settings(self):
        """Open settings dialog."""
        if self._settings_window is None or not self._settings_window.isVisible():
            self._settings_window = SettingsWindow(self.storage, self)
            self._settings_window.show()
        else:
            self._settings_window.raise_()
            self._settings_window.activateWindow()

    def on_document_activated(self, doc):
        """Create overlay panel for the activated document."""
        if not self.storage.overlay_panel_on:
            return

        # Ensure document has uid
        if not hasattr(doc, 'uid'):
            doc.addProperty("App::PropertyString", "uid", "CustomAttributes")
            doc.uid = str(uuid.uuid4())

        workbench = Gui.activeWorkbench().name() if Gui.activeWorkbench() else DEFAULT_WORKBENCH
        tools = get_tools_from_settings(self.storage, workbench, self.storage.tools)
        if not tools:
            return

        doc_panels = self.panels.get(doc.uid)
        if doc_panels and 'overlay' in doc_panels:
            return  # already exists

        window = Gui.getMainWindow()
        overlay_panel = OverlayPanel(
            parent=window,
            tools=tools,
            position=self.storage.position,
            orientation=self.storage.orientation,
        )
        self.panels.setdefault(doc.uid, {})['overlay'] = overlay_panel
        overlay_panel.show()

    def on_document_closed(self, doc):
        """Destroy overlay panel when document is closed."""
        if hasattr(doc, 'uid') and doc.uid in self.panels:
            panel_data = self.panels.pop(doc.uid)
            panel = panel_data.get('overlay')
            if panel:
                panel.destroy()

    def on_workbench_activated(self, wb):
        """Rebuild panels when workbench changes."""
        # Wait until workbench is fully loaded (has its tools)
        def check_loaded():
            if hasattr(wb, '__Workbench__'):
                # Refresh tool cache for this workbench
                list_wb_tools(self.storage, wb.name())
                self.rebuild_panels()
                return True
            return False

        if not check_loaded():
            timer = QtCore.QTimer()
            timer.timeout.connect(lambda: self._retry_workbench_load(wb, timer))
            timer.start(100)

    def _retry_workbench_load(self, wb, timer):
        if hasattr(wb, '__Workbench__'):
            timer.stop()
            timer.deleteLater()
            list_wb_tools(self.storage, wb.name())
            self.rebuild_panels()

    def rebuild_panels(self):
        """Recreate overlay panels for all active documents."""
        for doc_uid, panel_data in list(self.panels.items()):
            panel = panel_data.get('overlay')
            if panel:
                panel.destroy()
        self.panels.clear()

        # Recreate for each open document
        for doc in App.listDocuments().values():
            self.on_document_activated(doc)

    def shutdown(self):
        """Clean up resources when plugin is unloaded."""
        # Destroy all panels
        for doc_uid, panel_data in self.panels.items():
            panel = panel_data.get('overlay')
            if panel:
                panel.destroy()
        self.panels.clear()

        # Remove document observer
        if self.doc_observer:
            self.doc_observer.remove()
            self.doc_observer = None

        # Remove menu
        if self._menu:
            self._menu.deleteLater()
            self._menu = None

        # Disconnect signals
        window = Gui.getMainWindow()
        if window:
            try:
                window.workbenchActivated.disconnect(self.on_workbench_activated)
            except Exception:
                pass

        self._initialized = False