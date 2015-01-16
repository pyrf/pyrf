VERSION = (2, 7, 3, 'dev')
__version__ = ''.join(['-.'[type(x) == int]+str(x) for x in VERSION])[1:]
