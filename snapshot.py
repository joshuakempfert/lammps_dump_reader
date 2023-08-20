# -*- coding: utf-8 -*-
"""
Container module for Snapshot base class, as summarized below
"""

# Descriptor that only allows assignment once (intended to be during initialization)
from .common import readonly

from .visualize import render_snapshot

from . import sources

class Snapshot:
    """
    Abstract base class
    
    Instance represents the atoms and box of a LAMMPS simulation (i.e. a single dump)
    
    In this implementation, a snapshot always points to a source (i.e. a file) containing the atomic
    data. Therefore, atomic data cannot be modified unless you convert it to another format
    (e.g. atomman) and then convert that to a snapshot.
    
    Source is vague here to leave the door open for file formats besides LAMMPS dump files in the
    future. 
    
    ----------------------------------------------------------------------
    Instance variables:
        
    source (readonly)
        Object which contains atomic data which instance can request using its identifier
    
    identifier (readonly)
        Some value which is passed to source for it to identify the snapshot's atomic data
        
    custom
        Dict-like object containing user-defined global data for dump
        
    timestep (int)
        Timestep number
    
    n_atoms (int)
        Number of atoms in snapshot
        
    box (Box)
        Box object for snapshot
        
    atom_data (tuple, readonly)
        Headers of per-atom data stored
    """
    
    source = readonly()
    identifier = readonly()
    atom_data = readonly()
    
    def __init__(self, source, identifier):
        """Assign instance variables"""
        self.source = source
        self.identifier = identifier
        
    
    def __str__(self):
        """Create nicely formatted string of snapshot"""
        string = f"Timestep: {self.timestep}\n"
        string += f"Number of atoms: {self.n_atoms}\n"
        string += f"Per-atom data: {self.atom_data}\n"
        string += f"Box:\n {str(self.box)}"
        
        
        if len(self.custom) > 0:
            custom_str = ('\n').join(map(str, self.custom.items()))
            
            string += f"Custom: \n {custom_str}"
        
        return string
        
    __repr__ = __str__
    
    def to_atomman(self, *args, **kwargs):
        """
        Create atomman System object from snapshot.
        
        The atomman object will inherit the box properties from the snapshot and the atom data
        stored in the source
        
        *args and **kwargs are passed through as atomman.load("atom_dump", dump_str, *args, **kwargs)
        
        Returns: atomman system object
        """
        
        return type(self.source).snapshot_to_atomman(self, *args, **kwargs)
    
    def to_dump(self, ignore_custom = False):
        """
        Convert snapshot to LAMMPS dump string
        
        The dump string will contain the box properties, atomic data, and optionally the custom 
        global properties defined in the snapshot.
        
        Args:
            ignore_custom (bool): Whether to include custom properties in dump string, default True 
            
        Returns: string, LAMMPS dump file format
        """
        
        return type(self.source).snapshot_to_dump(self, ignore_custom)
    
    def read_dump(self):
        """Get string of dump stored in source"""
        return self.source.read_snapshot_dump(self.identifier)
    
    def render(self):
        """Use Ovito module to create interactive view of snapshot"""
        return render_snapshot(self)
    
    @classmethod
    def from_atomman(cls, system, timestep = 0, custom = None, **kwargs):
        """
        Create snapshot from atomman System object
        
        Args:
            system (Atomman System): Atomman system object
            timestep (int): Timestep of snapshot object
            custom (dict-like): Custom data for snapshot object
            
            **kwargs: Passed through to atomman method system.dump("atom_dump", **kwargs)
        """
        return sources.DumpFileSource.snapshot_from_atomman(system, timestep = timestep, custom = custom, **kwargs)
    
    
    