# -*- coding: utf-8 -*-
"""
Container module for Snapshots class, as summarized below.
"""

from pathlib import Path
import re
import numpy as np
from warnings import warn
from collections import abc

from . import sources
from .snapshot import Snapshot
from .box import Box
from .common import is_single_value

RESERVED_ITEMS = {"timestep", "n_atoms", "box_bounds", "box_tri", "box_BC"}
READONLY_ITEMS = {"n_atoms"}

def attempt_cast_string(array):
    """Attempts to cast string array to number"""
    
    try:
        numeric_array = np.array(array, dtype = float)
    except ValueError:
        return array
        
    
    if np.all(np.char.find(array, '.') == -1): # No decimals means integers
        return np.array(array, dtype = int)
    else:
        return numeric_array
        

class _SnapshotItemDescriptor():
    """
    This descriptor is created to represent Snapshot properties in Snapshot and Snapshots object
    
    The descriptor simply passes get and set requests of the given property to the owner object's
    items object, which handles the logic of the request.
    """
    
    def __get__(self, instance, owner):
        return instance.items[self.item_name]
        
    def __set__(self, instance, value):
        instance.items[self.item_name] = value
        
    def __init__(self, item_name):
        self.item_name = item_name

class _SnapshotItems(abc.MutableMapping):
    """
    Instances of this class provide a dict-like interface for the data contained in Snapshot objects
    
    Under the hood, the instance passes all requests through the linked _SnapshotsItems class, which
    holds the data for all Snapshot objects.
    
    ----------------------------------------------------------------------
    Instance variables:
        
    _snapshots_items
        _SnapshotsItems object of the Snapshots object which contains the snapshot
        
    _snapshot
        the Snapshot object which this object belongs to
    
    """
    
    def __init__(self, snapshot, snapshots_items):
        self._snapshots_items = snapshots_items
        self._snapshot = snapshot
        
    def __str__(self):
        return dict(self).__str__()
    
    def __repr__(self):
        return dict(self).__repr__()    
    
    def __iter__(self):
        """Iterates over keys"""
        return iter(self._snapshots_items)
        
    def __len__(self):
        """Number of keys"""
        return len(self._snapshots_items)
    
    def __setitem__(self, item, value):
        """Set snapshot item value"""
        self._snapshots_items.set_snapshot_value(self._snapshot, item, value)
    
    def __getitem__(self, item):
        """Get snapshot item value"""
        return self._snapshots_items.get_snapshot_value(self._snapshot, item)
    
    def __delitem__(self):
        raise RuntimeError("Delete operation not supported for individual snapshots")

class _SnapshotCustom(_SnapshotItems):
    """
    Functions identically to _SnapshotItems, except this object is passed a _SnapshotsCustom object
    """
    
    pass
    
class _SnapshotsItems(dict):
    """
    Provides a dict-like interface for Snapshots global data
    
    Instances of this class store the data for Snapshot objects contained in a Snapshots instance
    
    Class variables: used internally for type and shape enforcement of non-custom data
    
    ----------------------------------------------------------------------
    Instance variables:
        _snapshots: Snapshots object
        _num_snapshots: Number of Snapshot objects in Snapshots object
    
    """
    
    reserved = RESERVED_ITEMS  
    readonly = READONLY_ITEMS
    
    dtypes = {
        "timestep": int,
        "n_atoms": int,
        "box_BC": str,
        "box_bounds": float,
        "box_tri": float
    }
    
    shapes = {
        "timestep": tuple(),
        "n_atoms": tuple(),
        "box_BC": (3,2),
        "box_bounds": (3,2),
        "box_tri":(3,)
    }
        
    def __init__(self, snapshots, snapshots_old, attempt_cast_strings = False):
        """
            Creates _SnapshotsItems from iterable of Snapshot objects (snapshots_old) belonging to
            Snapshots object (snapshots)
            
            The Snapshot objects must all have the same custom properties defined, else an error
            will be raised.
            
            Args:
                snapshots (Snapshots)
                snapshots_old (iterable of Snapshot objects)
                attempt_cast_strings (bool): 
        
                attempt_cast_strings (bool): Whether to attempt to cast custom data that are strings
                to number. This is (usually) performed when custom data is read as a string from a 
                dump file (Default: False)
            
            Returns: _SnapshotsItems instance
        """
        
        if len(snapshots_old) > 0:
            # Keys should all be the same, so choose 0th arbitrarily
            keys = snapshots_old[0].items.keys()
            custom_keys = snapshots_old[0].custom.keys()
        else:
            # Prevent errors for empty snapshots object
            keys = []
            custom_keys = []
        
        key_set = set(keys)
        
        template_dict = {key: [] for key in keys}
        
        self._snapshots = snapshots
        self._num_snapshots = len(snapshots_old)
        
        for i, snapshot in enumerate(snapshots_old):
            if set(snapshot.items.keys()) != key_set:
                raise RuntimeError(f"Non-matching custom data at snapshot {i}")
                    
            for key, value in snapshot.items.items():
                template_dict[key].append(value)        
        
        if attempt_cast_strings:            
            for key in custom_keys:
                template_dict[key] = attempt_cast_string(template_dict[key])
            
                                         
        for item_name, value in template_dict.items():
            self.__setitem__(item_name, value, user = False)
        
    def set_snapshot_value(self, snapshot, item_name, value):
        """
        Sets the snapshot item's value in this object's array

        Called when a user edits a snapshot item from the Snapshot object
            e.g. snapshot.timestep = 10
        
        Note that the item must already exist (define new items at the Snapshot level)
        Also, the value must be shape-compatible with the ndarray representation at the Snapshots
        level
        
        Args:
            item_name (str): Name of item
            value (var): Value of item
        """
        
        assert item_name in self, "Key not found, create custom data from snapshots object"
        assert item_name not in self.readonly, f"{item_name} is read only"
        
        self[item_name][self._snapshots.index(snapshot)] = value
        
    
    def get_snapshot_value(self, snapshot, item_name):
        """
        Gets the snapshot item's from in this object's array

        Called when a user gets a snapshot item from the Snapshot object
            e.g. snapshot.timestep
        """
        assert item_name in self, "Key not found, create custom data from snapshots object"
        
        return self[item_name][self._snapshots.index(snapshot)]
    
    def __delitem__(self, item_name):
        """Delete item from items. Only valid for custom data"""
        
        assert item_name not in self.reserved, f"{item_name} cannot be deleted"
        
        super().__delitem__(item_name)
    
    def __setitem__(self, item_name, value, user = True):
        """
        Set an item's value. This is invoked when the user edits on the Snapshots level
        
            e.g. snapshots.items["timestep"] = 0
        
        Broadcasting capability is limited, so ensure value is correctly sized for predictable
        behavior
        
        readonly items (stored in cls.readonly) cannot be edited by the user
        
        Args:
            item_name (str): Name of item
            value (var): Value of item (for all Snapshot objects)
            user (bool): Whether the user is calling this (default True)
                Used to distiguish internal versus user requests
        """
        
        assert type(item_name) == str, "String keys only"
        assert (not user) or (item_name not in self.readonly), f"{item_name} is read only"
        
        dtype = self.dtypes.get(item_name)
        shape = self.shapes.get(item_name)
        
        value = np.array(value, dtype = dtype)
        value.flags.writeable = item_name not in self.readonly
        
        if is_single_value(value):
            value = np.repeat(value, self._num_snapshots, axis = 0)
        
        value_shape = value.shape[1:]
        assert (shape is None) or value_shape == shape, f"Expected {shape} shape, got {value_shape}"

        assert len(value) == self._num_snapshots, "Incorrectly sized input"
        
        super().__setitem__(item_name, value)


class _SnapshotsCustom(abc.MutableMapping):
    """
    Provides a dict-like interface for Snapshots custom global data
    
    Internally, this passes through to _SnapshotsItems, which handles all of the logic. However,
    this object filters item keys that are not custom
    
    See _SnapshotsItems for documentation on these methods
    """
    
    def __init__(self, snapshots_items):
        self._snapshots_items = snapshots_items
        
    def __iter__(self):
        return filter(lambda x: x not in RESERVED_ITEMS, iter(self._snapshots_items))
        
    def __len__(self):
        return len(self._snapshots_items) - len(RESERVED_ITEMS)
    
    def __str__(self):
        return dict(self).__str__()
    
    def __repr__(self):
        return dict(self).__repr__()
    
    def get_snapshot_value(self, snapshot, item_name):
        assert item_name not in RESERVED_ITEMS, "Key not found"
        
        return self._snapshots_items.get_snapshot_value(snapshot, item_name)
    
    def set_snapshot_value(self, snapshot, item_name, value):
        assert item_name not in RESERVED_ITEMS, f"{item_name} is reserved"
        
        return self._snapshots_items.set_snapshot_value(snapshot, item_name, value)
    
    def __setitem__(self, item_name, value):
        assert item_name not in RESERVED_ITEMS, f"{item_name} is reserved"
            
        self._snapshots_items[item_name] = value
    
    def __getitem__(self, item_name):
        assert item_name not in RESERVED_ITEMS, "Key not found"
        
        return self._snapshots_items[item_name]
    
    def __delitem__(self, item_name):
        assert item_name not in RESERVED_ITEMS, "Key not found"
        
        del self._snapshots_items[item_name]


class _ReferenceBox(Box):
    """
    Instance represents either a single or multiple LAMMPS boxes, depending on whether the box
    object was pulled from a snapshot instance or snapshots instance
    
    If multiple boxes, the first axis of all properties represents the box index. Otherwise,
    that axis is omitted.

    In arrays corresponding to spatial dimensions, the ordering always is (x, y, z) 
    
    
    Instance variables may be replaced or the object mutated. Broadcasting capability is limited,
    so be sure your array is the correct size if you are replacing
    
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
    
    
    BC = _SnapshotItemDescriptor("box_BC")
    bounds = _SnapshotItemDescriptor("box_bounds")
    tri = _SnapshotItemDescriptor("box_tri")
    
    def __bool__(self):
        # len causes issues with truthiness
        return True
    
    def __len__(self):
        """Return number of boxes stored"""
        # Decision to use tri is arbitrary
        
        if self.tri.ndim == 2:
            return len(self.tri)
        else:
            return 0
    
    def __init__(self, items):
        """
        Construct ReferenceBox
        
        items is either a _SnapshotItems or _SnapshotsItems object, which corresponds to either
        a snapshot or snapshots object, respectively.
        """
        
        self.items = items
    
    def __str__(self):
        n_boxes = len(self)
        
        if n_boxes > 0:
            # "Box" is representing multiple boxes
            return f"{n_boxes} boxes"
        else:
            return super().__str__()


class _ReferenceSnapshot(Snapshot):
    """    
    Instance represents the atoms and box of a LAMMPS simulation (i.e. a single dump).
    
    This object is always tied to a Snapshots object. This snapshot's global properties are mutable, 
    and editing them will propagate to the Snapshots object aswell.
    
    In this implementation, a snapshot always points to a source (i.e. a file) containing the atomic
    data. Therefore, atomic data cannot be modified unless you convert it to another format
    (e.g. atomman) and then convert that to a snapshot.
    
    ----------------------------------------------------------------------
    Instance variables:
        
    source (readonly)
        Object which contains atomic data which instance can request using its identifier
    
    identifier (readonly)
        Some value which is passed to source for it to identify the snapshot's atomic data
        
    timestep (int)
        Timestep number
    
    n_atoms (int, readonly)
        Number of atoms in snapshot
        
    box (Box)
        Box object for snapshot
        
    atom_data (tuple, readonly)
        Headers of per-atom data stored
        
    items (_SnapshotItems)
        dict-like object containing all data lumped into key-value pairs (usually for internal use)
        
    custom (_SnapshotCustom)
        Dict-like object containing user-defined global data for snapshot.
    """
    
    timestep = _SnapshotItemDescriptor("timestep")
    n_atoms = _SnapshotItemDescriptor("n_atoms")
    
    def __init__(self, source, identifier, atom_data, snapshots_items, snapshots_custom):
        """
        Creates snapshot object
        
        Args: 
            source, identifier, atom_data are self-explanatory (see docstring)
        
            snapshots_items (_SnapshotsItems): SnapshotsItems object corresponding to the
                snapshots object which this belongs to
            
            snapshots_custom (_SnapshotsCustom): SnapshotsCustom object corresponding to the
                snapshots object which this belongs to
        """
        
        
        super().__init__(source, identifier)
        
        self.atom_data = tuple(atom_data)
        
        self.items = _SnapshotItems(self, snapshots_items)
        self.custom = _SnapshotCustom(self, snapshots_custom)
        self.box = _ReferenceBox(self.items)

 
    @classmethod
    def from_existing(cls, snapshot, snapshots_items, snapshots_custom):
        """Clones existing snapshot. Args are same as for __init__"""
        
        return cls(snapshot.source, snapshot.identifier, snapshot.atom_data, snapshots_items, 
                   snapshots_custom)


class Snapshots():
    """    
    Represents an ordered group of snapshots. This should be one's main interaction with dump_reader.
    
    Every Snapshots object owns its contained Snapshot objects. Therefore, editing a snapshot in one
    Snapshots object will never affect a snapshot object in a different Snapshots object.
    
    The snapshot objects contained a Snapshots object are fixed. Therefore, operations like adding
    and slicing always create a new snapshots object.
    
    Snapshots objects collect the global-data of snapshot objects into ndarrays of size (N, ...),
    where N is the number of snapshots. Alternatively, you can edit properties on a snapshot object 
    and the changes will propagate here.
    
    ----------------------------------------------------------------------
    Instance variables:
        
    snapshots (tuple):
        snapshot objects contained in Snapshots
        
    timesteps ((N,) int ndarray):
        Timesteps of contained snapshot objects
        
    n_atoms ((N,) int ndarray, readonly)::
        # of atoms of contained snapshot objects
    
    boxes (_ReferenceBox):
        The boxes of contained snapshot objects.
    
    items (_SnapshotsItems)
        Dict-like object containing (N, ...) ndarrays for global data in snapshot objects 
    
    custom (_SnapshotsCustom)
        Dict-like object containing (N, ...) ndarrays for custom global data in snapshot objects
        
    new
        When sliced, a new snapshots object will be returned containing the corresponding snapshot
        objects; e.g. new[::-1]
        
    """
    
    def __iter__(self):
        """Returns iterator over contained snapshot objects"""
        return iter(self.snapshots)
    
    def __getitem__(self, index):
        """Returns snapshot object(s), where slicing is supported"""
        return self.snapshots[index]
    
    def __setitem__(self, index, values):
        raise RuntimeError("Attempt to modify immutable snapshots object")
    
    def index(self, *args, **kwargs):
        """Pass-through method to get index of snapshot object. See tuple.index"""
        return self.snapshots.index(*args, **kwargs)
    
    def __add__(self, object2):
        """
        Add either an individual snapshot or another snapshots object and return a new Snapshots
        object.
        
        Args:
            object2 (Snapshot or Snapshots): Object to add
            
        Returns:
            New snapshots object, where right-hand snapshot(s) appear later in index
        """
        
        if type(object2) is not type(self):
            if issubclass(type(object2), Snapshot):
                return type(self)(self.snapshots + (object2,))
            
            raise RuntimeError(f"Incompatible type {type(object2)} for sum")
        
        return type(self)(self.snapshots + object2.snapshots)
    
    
    def __radd__(self, object2):
        """Reverse add to handle snapshot + Snapshots case. See __add__"""
        
        if issubclass(type(object2), Snapshot):
            return type(self)((object2,) + self.snapshots)
        
        raise RuntimeError(f"Incompatible type {type(object2)} for sum")    
    
    def __str__(self):
        """Give nicely formatted str representation"""
        
        string = f"Number of snapshots: {len(self)}\n"
        string += f"Timesteps: {self.timesteps[0]}, {self.timesteps[1]}, {self.timesteps[2]}, ..., \
            {self.timesteps[-2]}, {self.timesteps[-1]}\n"
        
        if len(self.custom) > 0:
            string += f"Custom data: {', '.join(self.custom.keys())}"
        
        return string
    
    def __repr__(self):
        return self.snapshots.__repr__()
    
    def __len__(self):
        """Returns number of contained snapshot objects"""
        return len(self.snapshots)
    
    
    def write_dump(self, path, allow_overwrite = False, ignore_custom = False):
        """
        Write collection of snapshot objects to dump file.
        
        Args:
            path (Path or str): Path to write dump file
            allow_overwrite (bool): Whether to overwrite an existing file of the same path. If false
                                    and the path exists, an error will be raised (default False)
            
            ignore_custom (bool): Determines whether custom data is written to dump file or not
            
        Returns: None
        """
        
        with open(path, "w" if allow_overwrite else "x") as file:
            for snapshot in self:
                file.write(snapshot.to_dump(ignore_custom = ignore_custom))
    
    class _new():
        def __init__(self, instance):
            self.instance = instance
        
        def __getitem__(self, index):
            """Return sliced copy of snapshots"""
            return type(self.instance).from_index(self.instance, index)
        
  
    timesteps = _SnapshotItemDescriptor("timestep")
    n_atoms = _SnapshotItemDescriptor("n_atoms")
        
    def __init__(self, snapshots_old, attempt_cast_strings = False):
        """
        Constructor for Snapshots. Not recommended to call directly, use one of the class methods
        to get a Snapshots object
        
        Args:
            snapshots_old (list-like): Snapshot objects to create Snapshots from
            attempt_cast_strings (bool): Whether to attempt to cast custom data that are strings to
                number. This is performed when custom data is read as a string from a dump file
                Default: False
        """
        
        self.items = _SnapshotsItems(self, snapshots_old, attempt_cast_strings = attempt_cast_strings)        
        self.custom = _SnapshotsCustom(self.items)
        
        # Clone snapshot objects
        self.snapshots = tuple(_ReferenceSnapshot.from_existing(snapshot, self.items, self.custom) for snapshot in snapshots_old)    
        
        self.boxes = _ReferenceBox(self.items)

        self.new = type(self)._new(self)

    @classmethod
    def empty(cls):
        """Return Snapshots object with no Snapshot objects contained"""
        return cls([])

    
    @classmethod
    def from_atomman(cls, *args, **kwargs):
        """
        Creates Snapshots object containing one Snapshot from atomman
        
        Equivalent to Snapshots.from_snapshot(Snapshot.from_atomman(*args, **kwargs))
        
        Args: Passed through to Snapshot.from_atomman
        
        Returns:
            Snapshots object with single Snapshot
        """
        return cls.from_snapshot(Snapshot.from_atomman(*args, **kwargs))

    @classmethod
    def from_snapshot(cls, snapshot):
        """
        Creates Snapshots object containing one Snapshot
        Note that the contained Snapshot will be a clone of the provided snapshot
        
        Args:
            snapshot (Snapshot): Snapshot whose clone will be contained in Snapshots instance
            
        Returns: Snapshots object
        """
                    
        return cls([snapshot])
    
    def from_snapshots(cls, snapshots):
        """
        Creates Snapshots object from an iterable snapshots containing Snapshot objects
        Note that the contained Snapshots will be clones
        
        Args:
            snapshots (iterable of Snapshot objects)
            
        Returns: Snapshots object
        """
        return cls(snapshots)
    
    @classmethod
    def from_dump(cls, path):
        """
        Creates Snapshots object from a LAMMPS dump file
        
        Args:
            path (str of Path): Path of dump file
        
        Returns: Snapshots object
        """
        file = open(path, "r")
        source = sources.DumpFileSource(file)
        
        return cls(source.snapshots, attempt_cast_strings = True)
    
    @classmethod
    def from_index(cls, snapshots, index):
        """
        Creates Snapshots object from the subset of Snapshot objects indexed by index
        
        Used by new
        
        Args:
            index (int or slice): index(es) of Snapshot objects to include in new Snapshots
            
        Returns: Snapshots object
        """
        
        if type(index) == slice:
            return cls(snapshots[index])
        elif type(index) == int:
            return cls([snapshots[index]])
        else:
            raise RuntimeError(f"Unexpected type {type(index)} in snapshots")
     
