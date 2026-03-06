def global_exception_handler(exctype, value, tb):
    import traceback
    import FreeCADGui as Gui

    app = Gui.getMainWindow()
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    print('=' * 60)
    print('EXCEPTION CAUGHT:')
    print(error_msg)
    print('=' * 60)
    
    # Send to FreeCAD's Report View
    app.Console.PrintError(error_msg)


def get_tools_from_settings(storage, workbench: str, data: dict) -> tuple:
    def get_parts(workbench, name):
        parts = name.split('_')
        if len(parts) > 1:
            tool_workbench, tool_name = parts
        else:
            tool_workbench, tool_name = workbench, name
        return tool_workbench, tool_name

    tools = data.get(workbench, {})
    actions = storage.wbtools.get(workbench, {})
    panel_tools = []
    for name, tool in tools.items():
        print('LOAD TOOL: ', name, tool)
        tool_group = []
        tool_workbench, tool_name = get_parts(workbench, name)
        action_name = tool['action_name']
        tool_group.append((
            tool_workbench,
            tool['pub_name'],
            (tool['action_name'], ),
            actions[action_name].icon(),
        ))
        if children := tool.get('children', {}).values():
            for tool_ in children:
                action_name = tool_['action_name']
                tool_workbench, tool_name = get_parts(workbench, name)
                tool_group.append((
                    tool_workbench,
                    tool_['pub_name'],
                    (tool_['action_name'], ),
                    actions[action_name].icon(),
                ))
        panel_tools.append(tool_group)
    print('Load tools for workbench from settings.')
    return panel_tools

