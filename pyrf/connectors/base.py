from functools import wraps

SCPI_PORT = 37001
VRT_PORT = 37000

def sync_async(f):
    """
    This function decorator turns a generator method in a device class
    like :class:`pyrf.devices.thinkrf.WSA`
    into a simple method that either blocks until the generator is
    complete, or returns an object for async use, such as a Twisted
    Deferred.

    The behaviour of this function depends on the connector class used
    by the device, stored as self.connector.
    """
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        gen = f(self, *args, **kwargs)
        return self.connector.sync_async(gen)
    return wrapper


