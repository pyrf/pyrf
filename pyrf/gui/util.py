
from hotkey_util import *

def frequency_text(hz):
    """
    return hz as readable text in Hz, kHz, MHz or GHz
    """
    if hz < 1e3:
        return "%.3f Hz" % hz
    elif hz < 1e6:
        return "%.3f kHz" % (hz / 1e3)
    elif hz < 1e9:
        return "%.3f MHz" % (hz / 1e6)
    return "%.3f GHz" % (hz / 1e9)
    
def hotkey_util(layout,event):
    """
    modify elements in the gui layout based on which key was pressed
    """
    

    if arrow_dict.has_key(str(event.key())):
        hotkey =  arrow_dict[str(event.key())]
    else:
        hotkey = str(event.text()).upper()
        
    if hotkey_dict.has_key(hotkey):
        hotkey_dict[hotkey](layout)

      



