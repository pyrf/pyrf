

def _grid_control(layout):
    """
    disable/enable plot grid in layout
    """
    layout.grid_enable = not(layout.grid_enable)
    layout.grid_control(layout.grid_enable)

hotkey_dict = {'G': _grid_control} 


    