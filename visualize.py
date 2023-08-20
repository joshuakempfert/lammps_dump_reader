# -*- coding: utf-8 -*-
"""
Contains function for rendering a snapshot using Ovito
"""

import tempfile
import os

class snapshot_temp_file:
    """
    This class is written so that a context-manager interface can be used with the snapshot temp file
    to ensure it deletes properly, even if the program exits improperly.
    
    Instance variables:
        file (TemporaryFile)
        path: Path of file
        
    """
    
    def __init__(self, snapshot):
        self.snapshot = snapshot        
        
    def __enter__(self):
        # Create temp file for Ovito to use
        self.file = tempfile.NamedTemporaryFile(mode = "w", delete = False)
        self.path = self.file.name
        self.file.write(self.snapshot.to_dump())
        self.file.close()
        return self.path

    def __exit__(self, exc_type, exc_value, traceback):
        # Delete temp file
        os.remove(self.path)
    
    

def render_snapshot(snapshot):
    """Creates interactive window containing the atoms in snapshot"""
    # Ovito requires file, so create temporary
    # Use context manager so that temp_file will be cleaned up even if an error occurs
    with snapshot_temp_file(snapshot) as path:
        # Lazy load so that Ovito module isn't required unless user calls this function
        from .ovito_tool import render
        render(path)