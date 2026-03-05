def get_tools_from_settings(storage, workbench: str, data: dict) -> tuple:
    try:
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
            tool_group = []
            tool_workbench, tool_name = get_parts(workbench, name)
            action_name = tool['action_name']
            print('ACTIONS 1: ', action_name)
            tool_group.append((
                tool_workbench,
                tool['pub_name'],
                (tool['action_name'], ),
                actions[action_name].icon(),
            ))
            if children := tool.get('children', []):
                for action_name in children:
                    print('ACTIONS 2: ', action_name)
                    if tool_ := tools.get(action_name):
                        tool_workbench, tool_name = get_parts(workbench, name)
                        tool_group.append((
                            tool_workbench,
                            tool_['pub_name'],
                            (tool_['action_name'], ),
                            actions[action_name].icon(),
                        ))
            panel_tools.append(tool_group)
        return panel_tools
    except Exception as e:
        print('EXCEPTION: ', e)
        raise

