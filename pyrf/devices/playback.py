from pyrf.devices.thinkrf_properties import wsa_properties

class Playback(object):
    def __init__(self, device_class, device_identifier):
        # all we support for now
        assert device_class == 'thinkrf.WSA'
        self.properties = wsa_properties(device_identifier)

