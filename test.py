# if __name__ == '__main__':
tools = {
    'PartDesignWorkbench': {
        'PartDesign_SubShapeBinder': {
            'pub_name': 'Sub-Shape Binder',
            'action_name': 'PartDesign_SubShapeBinder'
            
        },
        'Part_CheckGeometry': {
            'pub_name': 'Check Geometry',
            'action_name': 'Part_CheckGeometry',
            'children': [
                'PartDesign_SubShapeBinder',
                'Sketcher_ValidateSketch'
            ]
        },
        'Sketcher_ValidateSketch': {
            'pub_name': 'Validate Sketch',
            'action_name': 'Sketcher_ValidateSketch'
        },
        'PartDesign_Clone': {
            'pub_name': 'Clone',
            'action_name': 'PartDesign_Clone'
        },
        'PartDesign_Pad': {
            'pub_name': 'Pad',
            'action_name': 'PartDesign_Pad'
        }
    }
}
    
def get_tools_from_settings(storage, workbench: str, data: dict) -> tuple:
    def get_parts(workbench, name):
        parts = name.split('_')
        if len(parts) > 1:
            tool_workbench, tool_name = parts
        else:
            tool_workbench, tool_name = workbench, name
        return tool_workbench, tool_name

    tools = data.get(workbench, {})
    panel_tools = []
    for name, tool in tools.items():
        tool_group = []
        tool_workbench, tool_name = get_parts(workbench, name)
        tool_group.append((
            tool_workbench,
            tool['pub_name'],
            (tool['action_name'], ),
            'view-top',
        ))
        if children := tool.get('children', []):
            for action_name in children:
                if tool_ := tools.get(action_name):
                    tool_workbench, tool_name = get_parts(workbench, name)
                    tool_group.append((
                        tool_workbench,
                        tool_['pub_name'],
                        (tool_['action_name'], ),
                        'view-top',
                    ))
        panel_tools.append(tool_group)
    return panel_tools

# print(get_tools_from_settings(None, 'PartDesignWorkbench', tools))