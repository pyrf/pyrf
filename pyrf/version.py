VERSION = (2, 8, 0, 'dev2')
__version__ = ''.join(['-.'[type(x) == int]+str(x) for x in VERSION])[1:]
