
def select_fstart(layout):
    layout._fstart.setStyleSheet("Background-color: green")
    layout._cfreq.setStyleSheet("Background-color: None")
    layout._fstop.setStyleSheet("Background-color: None")

def select_center(layout):
    layout._cfreq.setStyleSheet("Background-color: green")
    layout._fstart.setStyleSheet("Background-color: None")
    layout._fstop.setStyleSheet("Background-color: None")

def select_fstop(layout):
    layout._fstop.setStyleSheet("Background-color: Green")
    layout._fstart.setStyleSheet("Background-color: None")
    layout._cfreq.setStyleSheet("Background-color: None")

def change_item_color(item, textColor, backgroundColor):
    item.setStyleSheet("Background-color: %s; color: %s" % (textColor, backgroundColor)) 

