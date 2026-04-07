import FreeCADGui as Gui
from PySide import QtGui

DEFAULT_WORKBENCH = "PartDesignWorkbench"


def list_workbenches():
    workbenches = Gui.listWorkbenches()
    return {workbenches[name].MenuText: name for name in sorted(workbenches)}


def find_workbench_by_sysname(storage, sys_name: str) -> str:
    for name, sys_name_ in storage.workbenches.items():
        if sys_name_ == sys_name:
            return name
    return ""


def get_wb_name(command: str) -> str:
    parts = command.split("_")
    return parts[0] if parts[0] else "None"


def list_wb_tools(storage, wb_name: str):
    actions = storage.wbtools.get(wb_name, {})

    if actions:
        return actions

    exclude = ("File", "Edit", "Help", "Clipboard")
    window = Gui.getMainWindow()

    try:
        print('original_WB', original_wb)
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
    
