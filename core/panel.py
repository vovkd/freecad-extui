import FreeCAD as App
import FreeCADGui as Gui

from overlay_toolbar import OverlayPanel


def setup_overlay_panel(doc=None, storage=None):
    if doc is None:
        doc = App.ActiveDocument
    if storage is None:
        window = Gui.getMainWindow()
        storage = window.extui["storage"]

    workbench = Gui.activeWorkbench().name()
    from utils import get_tools_from_settings

    tools = get_tools_from_settings(storage, workbench, storage.tools)

    if storage.overlay_panel_on and tools:
        window = Gui.getMainWindow()
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


def destroy_overlay_panel():
    window = Gui.getMainWindow()
    panels = window.extui["panels"].items()
    for key, item in panels:
        panel = item.get("overlay")
        if panel:
            window.extui["panels"][key].pop("overlay")
            panel.destroy()


def rebuild_panels():
    window = Gui.getMainWindow()
    if hasattr(window, "extui"):
        destroy_overlay_panel()
        setup_overlay_panel()
