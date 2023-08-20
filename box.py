# -*- coding: utf-8 -*-
"""
Container module for Box base class, as summarized below
"""

import numpy as np

class Box:
    """
    Abstract base class representing either a single or multiple LAMMPS boxes
    
    If multiple boxes, the first axis of all properties represents the box index. Otherwise,
    that axis is omitted.

    In arrays corresponding to spatial dimensions, the ordering always is (x, y, z) 
    
    ----------------------------------------------------------------------
    Instance variables (settable):
        
    bounds
        Bounds of box in space; (..., 3, 2) nd float array, where the first dim is spatial and the 
        second dim is (lo, hi)
        
    tri
        Triclinic tilt factors; (..., 3), where the ordering is (xy, xz, yz). All zero if not 
        triclinic
        
    BC
        BC char of 6 surfaces of box; (..., 3, 2) ndarray, where first dim is spatial and the second
        dim is the surface (lo, hi). See LAMMPS docs for BC char codes        
    """
    
    @property
    def is_tri(self):
        """Whether box is triclinic (i.e. any non-zero tilt factors)"""
        return np.any(self.tri != 0, axis = -1)
    
    @property
    def lx(self):
        """Length of box in X dimension"""
        return self.bounds[..., 0, 1] - self.bounds[..., 0, 0]
    
    @property
    def ly(self):
        """Length of box in Y dimension"""
        return self.bounds[..., 1, 1] - self.bounds[..., 1, 0]
    
    @property
    def lz(self):
        """Length of box in Z dimension"""
        return self.bounds[..., 2, 1] - self.bounds[..., 2, 0]
    
    @property
    def size(self):
        """Length of box in each dimension as (..., 3) ndarray"""
        return self.bounds[..., 1] - self.bounds[..., 0]
    
   
    @property
    def cx(self):
        """Center of box in x dimension"""
        return (self.bounds[..., 0, 1] + self.bounds[..., 0, 0])/2
    
    @property
    def cy(self):
        """Center of box in y dimension"""
        return (self.bounds[..., 1, 1] + self.bounds[..., 1, 0])/2
    
    @property
    def cz(self):
        """Center of box in z dimension"""
        return (self.bounds[..., 2, 1] + self.bounds[..., 2, 0])/2

    @property
    def center(self):
        """Center of box formatted as (..., 3) ndarray"""
        return (self.bounds[..., 1] + self.bounds[..., 0])/2

    @property
    def xy(self):
        """XY triclinic tilt factor"""
        return self.tri[..., 0]
    
    @property
    def xz(self):
        """XZ triclinic tilt factor"""
        return self.tri[..., 1]
    
    @property
    def yz(self):
        """YZ triclinic tilt factor"""
        return self.tri[..., 2]

    def _get_BC_string(self):
        """Join BC chars together in dim-grouped format, e.g. pp pp pp"""
        BC = map(lambda d: f"{d[0]}{d[1]}", self.BC)
        
        return ' '.join(BC)

    def __str__(self):
        """Give nicely formatted str representation"""
        string = ""
        
        string += f"BC: {self._get_BC_string()}\n"
        string += f"Size: {self.lx} x {self.ly} x {self.lz}\n"
        string += f"Center: {self.cx}, {self.cy}, {self.cz}\n"
        
        if self.is_tri:
            string += f"Tilt factors (xy, xz, yz): {', '.join(map(str, self.tri))}\n"   
        
        return string
    
    def __repr__(self):
        return self.__str__()
    
    