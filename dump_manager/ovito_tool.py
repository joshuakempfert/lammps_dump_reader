# -*- coding: utf-8 -*-
"""
Boilerplate code for the interactive Ovito gui sourced from:
   https://www.ovito.org/docs/current/python/modules/ovito_vis.html#ovito.vis.Viewport.create_qt_widget
"""

import sys, os

# Future versions of OVITO will use Qt6 & PySide6, older versions use Qt5 & PySide2.
# Please pick the right PySide version for import.
if os.getenv('QT_API') == 'pyside6': 
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication
else: 
    from PySide2.QtCore import QEventLoop, QTimer
    from PySide2.QtWidgets import QApplication

# Create a global Qt application object - unless we are running inside the 'ovitos' interpreter, 
# which automatically initializes a Qt application object.
if not QApplication.instance():
    is_ovitos = False
    myapp = QApplication(sys.argv)
else:
    is_ovitos = True

# Note: Import the ovito package AFTER the QApplication object
# has been created. Otherwise, Ovito would automatically create its own 
# QCoreApplication object, which won't let us display GUI widgets.
from ovito.io import import_file
from ovito.vis import Viewport

def render(file_name, width = 500, height = 400, name = "OVITO Viewport", customize = None):
    # Import model and add it to visualization scene.
    pipeline = import_file(file_name)
    pipeline.add_to_scene()
    
    # Create a virtual Viewport.
    vp = Viewport(type=Viewport.Type.Perspective, camera_dir=(2, 1, -1))
    
    if customize is not None:
        customize(pipeline, vp)
    
    # Create a visible GUI widget associated with the viewport.
    widget = vp.create_qt_widget()
    widget.resize(width, height)
    widget.setWindowTitle(name)
    widget.show()
    vp.zoom_all((widget.width(), widget.height()))
    
    # Shut down application when the user closes the viewport widget.
    widget.destroyed.connect(QApplication.instance().quit)
    
    # Start the Qt event loop.
    if not is_ovitos:
        # When a standard Python interpreter is used to run this script, start the 
        # application's main event loop to begin UI event processing.
        sys.exit(myapp.exec_()) 
    else:
        # When running this script with the 'ovitos' interpreter, a Qt event loop is already active.
        # Start a nested event loop then, just for this little demo program.
        eventLoop = QEventLoop()
        widget.destroyed.connect(eventLoop.quit) # Stop event loop when user closes the viewport widget.
        eventLoop.exec_()
