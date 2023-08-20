# -*- coding: utf-8 -*-
"""
Internal module of dump_reader handling parsing of LAMMPS files
"""

from pathlib import Path
import re
import numpy as np
import tempfile

from .snapshot import Snapshot
from .box import Box
from .common import has_no_length, readonly

def jump_lines(f, num):
    """Skip past num lines in file f"""
    
    readline = f.readline # Localize for speed
    
    for _ in range(num):
        readline()


def read_lines(f, num):
    """Read num lines from f and return as list"""
    
    lines = []
    
    # Localize for speed
    readline = f.readline
    append = lines.append
    
    for _ in range(num):
        append(readline())
        
    return lines

def get_position(f):
    """Get file position handle"""
    return f.tell()

def set_position(f, N):
    """Set file position using handle"""
    f.seek(N)
    
    
def str_starts_with(long_str, short_str):
    """self-explanatory"""
    return long_str[0:len(short_str)] == short_str


class SourceBox(Box):
    """
    Instance represents a box originating from a source (e.g. a file). Box properties are immutable
    because they originate from a reference.
    
    Instances always refers to a single box only, so there is no ... dimension

    In arrays corresponding to spatial dimensions, the ordering always is (x, y, z) 
    
    ----------------------------------------------------------------------
    Instance variables (immutable):
        
    bounds
        Bounds of box in space; (3, 2) nd float array, where the first dim is spatial and the second
        dim is (lo, hi)
        
    tri
        Triclinic tilt factors; (3), where the ordering is (xy, xz, yz). All zero if not triclinic
        
    BC
        BC char of 6 surfaces of box; (3, 2) ndarray, where first dim is spatial and the second dim
        is the surface (lo, hi). See LAMMPS docs for BC char codes
    """
    
    BC = readonly()    
    bounds = readonly()
    tri = readonly()
    
    def __init__(self, BC, x_data, y_data, z_data):
        """
        Create immutable source box, with data inputs originating from those specified in LAMMPS
        dump
        
        Args:
            BC - List of BC strings for each dim (e.g. ["pp", "pp", "pp"])
            x_data - List of strings for each numeric entry in X data
            y_data - List of strings for each numeric entry in Y data
            z_data - List of strings for each numeric entry in Z data
        """
        
        self.BC = np.empty((3, 2), dtype = str)
        
        self.BC[0] = list(BC[0]) # Separate str
        self.BC[1] = list(BC[1])
        self.BC[2] = list(BC[2])
        
    
        self.bounds = np.empty((3, 2))
        
        self.bounds[0] = x_data[0:2]
        self.bounds[1] = y_data[0:2]
        self.bounds[2] = z_data[0:2]
        
        # Detect if tri-clinic based off whether tilt factors are provided by LAMMPS
        if len(x_data) == 3:
            self.tri = np.array([x_data[2], y_data[2], z_data[2]], dtype = float)
        else:
            self.tri = np.zeros(3)
        
        # Lock arrays
        self.BC.flags.writeable = False
        self.bounds.flags.writeable = False
        self.tri.flags.writeable = False       



class SourceSnapshot(Snapshot):
    """    
    Instance represents the atoms and box of a LAMMPS simulation (i.e. a single dump). This snapshot
    type is completely immutable, as it points directly to data from a source (i.e. a file)
    
    In this implementation, a snapshot always points to a source (i.e. a file) containing the atomic
    data. Therefore, atomic data cannot be modified unless you convert it to another format
    (e.g. atomman) and then convert that to a snapshot.
    
    ----------------------------------------------------------------------
    Instance variables (all readonly):
        
    source
        Object which contains atomic data which instance can request using its identifier
    
    identifier
        Some value which is passed to source for it to identify the snapshot's atomic data
        
    custom
        Dict-like object containing user-defined global data for dump
        
    timestep (int)
        Timestep number
    
    n_atoms (int)
        Number of atoms in snapshot
        
    box (Box)
        Box object for snapshot
        
    atom_data (tuple)
        Headers of per-atom data stored
        
    items (dict)
        Contains all data lumped into key-value pairs (for internal use) 
    """
    
    n_atoms = readonly()
    box = readonly()
    custom = readonly()
    timestep = readonly()

    def __init__(self, source, identifier, timestep, n_atoms, atom_data, box, custom):
        """
        Assigns instance variables to respective arguments
        
        Args: all self-explanatory (see class docstring)
        """
        
        super().__init__(source, identifier)
        
        self.atom_data = tuple(atom_data)
        
        self.timestep = timestep
        self.n_atoms = n_atoms
        self.box = box
        self.custom = custom

        self.items = self.custom.copy()
        self.items["timestep"] = self.timestep
        self.items["n_atoms"] = self.n_atoms
        
        self.items["box_bounds"] = self.box.bounds
        self.items["box_tri"] = self.box.tri
        self.items["box_BC"] = self.box.BC



class DumpFileSource():
    """
    Instances of this class parse a LAMMPS dump file into snapshot objects which contain the global
    dump data and a position handle to lookup the per-atom data in the file
    
    Class variables are used as constants and are self-explanatory, so they will not be documented
    
    ----------------------------------------------------------------------
    Instance variables:
        
        file: File object of dump
        
        snapshots: list containing SourceSnapshot objects from dump
        
        snapshot_seek_info: list containing the file position for each SourceSnapshot in the dump file
    """
    
    item_pattern = re.compile("^ITEM: (.+)")
    sep_pattern = re.compile("(\S+)")
    
    space_pattern = re.compile("\s")
    
    item_str = "ITEM: "
    
    timestep_item_str = "TIMESTEP"
    n_atoms_item_str = "NUMBER OF ATOMS"
    atoms_item_str = "ATOMS"        
    box_item_str = "BOX BOUNDS"
        
    atoms_pattern = re.compile("ITEM: ATOMS (?s:.+)")
    box_pattern = re.compile("(ITEM: BOX BOUNDS (?s:.+))ITEM: ")
    
    @classmethod
    def box_to_dump(cls, box):
        """Converts box object to LAMMPS dump box representation"""
        tri_order = ["xy", "xz", "yz"]        
        
        string = "ITEM: BOX BOUNDS "
        
        if box.is_tri: 
            string += ' '.join(tri_order)
        
        string += ' ' + box._get_BC_string() + '\n'
        
        for axis, tri in zip(range(0, 3), box.tri):
            l = list(box.bounds[axis, 0:2]) 
            if box.is_tri:
                l.append(tri)
            
            string += ' '.join(map(str, l)) + '\n'
        
        return string
    
    @classmethod
    def atomman_to_dump(cls, system, timestep = 0, custom = None, **kwargs):
        """
        Convert atomman to LAMMPS dump string format
        
        Args:
            system (Atomman System): Atomman system object
            timestep (int): Timestep
            custom (dict-like): Custom data (default None)
            
            **kwargs: Passed through to atomman method system.dump("atom_dump", **kwargs)
            
        Returns:
            string of LAMMPS dump
        """
        
        dump_string = system.dump("atom_dump", **kwargs)
        
        box_string = cls.read_dump_box(dump_string)
        atoms_string = cls.read_dump_atoms(dump_string)
        
        header_string = cls.get_dump_header(timestep, system.natoms, custom = custom)
        
        return header_string + box_string + atoms_string
    
    @classmethod
    def snapshot_from_atomman(cls, system, timestep = 0, custom = None, **kwargs):
        """
        Create SourceSnapshot from atomman System
        
        Args:
            system (Atomman System): Atomman system object
            timestep (int): Timestep of snapshot
            custom (dict-like): Custom data for snapshot (default None)
            
            **kwargs: Passed through to atomman method system.dump("atom_dump", **kwargs)
            
        Returns:
            SourceSnapshot of atomman System
        """
        string = cls.atomman_to_dump(system, timestep, custom, **kwargs)
        
        # Store as a file for RAM cleanup
        file = tempfile.TemporaryFile("r+")
        file.write(string)
        file.seek(0) # Return to beginning
                
        return cls(file).snapshots[0]
    
    @classmethod
    def snapshot_to_atomman(cls, snapshot, *args, **kwargs):
        """
        Create atomman System object from snapshot.
        
        The atomman object will inherit the box properties from the snapshot and the atom data
        stored in the source
        
        *args and **kwargs are passed through as atomman.load("atom_dump", dump_str, *args, **kwargs)
        
        Returns: atomman system object
        """
        
        dump_str = snapshot.to_dump(ignore_custom = True) # Atomman is not guaranteed to support custom format
        
        # Lazy-load atomman so that module is not required unless user calls functions involving it
        from atomman import load
        
        system = load("atom_dump", dump_str, *args, **kwargs) # Load timestep into atomman for analysis
        
        return system
    
    @classmethod
    def get_dump_header(cls, timestep, n_atoms, box = None, custom = None):
        """
        Get dump header string in LAMMPS format
        
        Args:
            timestep (int)
            n_atoms (int)
            box (Box)
            custom (dict)
        
        Returns: string containing the dump header
        """
        
        string = ""
    
        def addline(line):
            nonlocal string
            string += line + "\n"
    
        addline(cls.item_str + cls.timestep_item_str)
        addline(str(timestep))
        addline(cls.item_str + cls.n_atoms_item_str)
        addline(str(n_atoms))
        
        if custom:
            for key, value in custom.items():
                addline(cls.item_str + key)
                addline(cls.custom_value_to_dump(value))
                
        if box:
            string += cls.box_to_dump(box)
            
        return string
    
    @classmethod
    def get_snapshot_dump_header(cls, snapshot, ignore_custom = False):
        """Simple wrapper for get_dump_header"""
        return cls.get_dump_header(snapshot.timestep, snapshot.n_atoms, 
                                   snapshot.box, None if ignore_custom else snapshot.custom)
        
    
    @classmethod
    def read_dump_box(cls, string):
        """Given a dump string, return only the portion containing the box data"""
        return cls.box_pattern.search(string).group(1)
    
    @classmethod
    def read_dump_atoms(cls, string):
        """Given a dump string, return only the portion containing the atomic data"""
        return cls.atoms_pattern.search(string).group(0)
    
    @classmethod
    def snapshot_to_dump(cls, snapshot, ignore_custom = False):
        """
        Convert snapshot to LAMMPS dump string
        
        The dump string will contain the box properties, atomic data, and optionally the custom 
        global properties defined in the snapshot.
        
        Args:
            ignore_custom (bool): Whether to include custom properties in dump string, default True 
            
        Returns: string, LAMMPS dump file format
        """
        
        full_str = snapshot.read_dump()
        
        atom_str = cls.read_dump_atoms(full_str)
        # Other data can change, but atoms remain constant
        
        header_str = cls.get_snapshot_dump_header(snapshot, ignore_custom = ignore_custom)
        
        return header_str + atom_str
    
    @classmethod
    def custom_value_to_dump(cls, value):
        """Convert custom data value to a clean string format for use in dump file"""
        
        # Value is either ndarray or a primitive type        
        def primitive_to_string(f):
            f = str(f)
            if cls.space_pattern.search(f) is not None:
                raise RuntimeError("Space-like characters not allowed in custom data entries")
            return f
                
        if has_no_length(value):
            return primitive_to_string(value)
        else:
            # 1D or greater ndarray
            string_array = np.vectorize(primitive_to_string)(value)
            
            # Collapse redundant dimensions
            if np.any(np.array(string_array.shape) == 1):
                string_array = string_array.flatten()
            
            assert string_array.ndim <= 2, "Custom data is only allowed to 2 dimensions"
            
            if string_array.ndim == 1:
                return '\n'.join(string_array)
            else: # 2 dims
                print(string_array, string_array.shape)
                return '\n'.join(map(lambda row: ' '.join(row), string_array))
     
    
    @classmethod
    def parse_custom_data(cls, lines):
        """Read custom data string and attempt to convert to ndvalue"""
        
        array = [cls.sep_pattern.findall(line) for line in lines]
        
        ndvalue = np.array(array, dtype = str) # Let numpy determine if shape is valid
        
        # Flatten column vectors to single dimension
        is_single = np.array(ndvalue.shape) == 1
        
        if np.all(is_single):
            ndvalue = ndvalue[0, 0]
        elif np.any(is_single):
            ndvalue = ndvalue.flatten()
        
        # Note: DumpFileSource does not attempt to cast to a numeric type
        
        return ndvalue
     
    def read_snapshot_dump(self, identifier):
        """Get string of dump stored in file"""
        assert 0 <= identifier < len(self.snapshots), f"Invalid identifier {identifier} when attempting to read snapshot"
        # Could store these as attrs on snapshot, but that seems unclean
        position, n_lines = self.snapshot_seek_info[identifier]
        
        set_position(self.file, position)
        
        return ''.join(read_lines(self.file, n_lines))        
 
    def __del__(self):
        """Close file when out of scope"""
        self.file.close()
    
    def __init__(self, file):
        """
        Parses dump file, creates Snapshot objects, and returns DumpFileSource object
        
        Args:
            file (str or Path): location of dump file
        """
        
        self.file = file
        
        self.snapshots = []
        
        self.snapshot_seek_info = []
        
        # Locals for current snapshot in loop
        
        # Need to track these so we can grab dump strings from file later
        snapshot_seek_position, snapshot_n_lines = None, 0
        # Data for snapshot object
        snapshot_timestep, snapshot_n_atoms, snapshot_box = None, None, None
        custom_snapshot_items = {}

        # Tracked for error reporting
        curr_line_position = 0

        def readline():
            # Readline but increment counters
            nonlocal snapshot_n_lines, curr_line_position
            snapshot_n_lines += 1
            curr_line_position += 1
            return self.file.readline()
        
        current_line = None
        
        while True:
            if snapshot_seek_position == None:
                snapshot_seek_position = get_position(self.file)

            line = current_line or readline()
            current_line = None
            
            if not line:
                break
            
            
            item_match = self.item_pattern.match(line)
            
            assert item_match, f"Dump format error at line {curr_line_position}"
            
            sep_items = self.sep_pattern.findall(item_match.group(1))
            
            item_str = sep_items[0]
                        
            if item_str == self.atoms_item_str:
                # atoms_item_str comes last, so collect data and create Snapshot object
                assert snapshot_timestep is not None, f"Missing timestep header info at line {curr_line_position}"
                assert snapshot_n_atoms is not None, f"Missing natoms header info at line {curr_line_position}"
                assert snapshot_box is not None, f"Missing box header info at line {curr_line_position}"
                
                snapshot_n_lines += snapshot_n_atoms
                
                new_snapshot = SourceSnapshot(self, len(self.snapshots), snapshot_timestep,
                                              snapshot_n_atoms, sep_items[1:], snapshot_box, custom_snapshot_items)
                
                self.snapshots.append(new_snapshot)
                self.snapshot_seek_info.append([snapshot_seek_position, snapshot_n_lines])
                
                # Skip past atomic data
                jump_lines(self.file, snapshot_n_atoms)
                
                # Reset locals
                custom_snapshot_items = {}
                snapshot_seek_position, snapshot_n_lines = None, 0
                snapshot_timestep, snapshot_n_atoms, snapshot_box = None, None, None
            elif item_str == self.timestep_item_str:
                snapshot_timestep = int(readline().strip())
            elif len(sep_items) > 1 and (' ').join(sep_items[0:2]) == self.box_item_str:
                line1, line2, line3 = readline(), readline(), readline()
                                
                x_data = self.sep_pattern.findall(line1)
                y_data = self.sep_pattern.findall(line2)
                z_data = self.sep_pattern.findall(line3)
                                
                snapshot_box = SourceBox(sep_items[::-1][0:3][::-1], x_data, y_data, z_data)
                
            elif len(sep_items) == 3 and (' ').join(sep_items[0:3]) == self.n_atoms_item_str:
                snapshot_n_atoms = int(readline().strip())
            else:
                # Parsing for custom item occurs if item is not recognized as built-in
                item_name = ' '.join(sep_items)
                lines = []
                
                while True:
                    current_line = readline()
                    
                    if self.item_pattern.match(current_line) is not None:
                        break
                    elif not current_line:
                        # dumps should always end with per-atom data
                        raise RuntimeError(f"Unexpected EOF during custom item {item_name} parsing")
                    
                    
                    lines.append(current_line)
                
                if not lines: # Empty data is not allowed
                    raise RuntimeError("Missing data for custom item {item_name}")
                
                # Parse
                custom_snapshot_items[item_name] = type(self).parse_custom_data(lines)
                
                
