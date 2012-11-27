from distutils.core import setup
import py2exe

setup(
    console=['wsa4000.py'],
    options={'py2exe':{
        'compressed':1,
        'bundle_files':1,
        'excludes':['Tkconstants', 'Tkinter', 'tcl'],
        }},
    zipfile=None,
    )
