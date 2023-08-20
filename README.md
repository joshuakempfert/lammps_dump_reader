## Description
This is a LAMMPS dump file parser/manipulator.

## Files 
- 'dump_reader': Package for parsing and manipulating LAMMPS dump files
	- 'box.py': Internal module implementing Box class
	- 'common.py': Internal module containing some utilities
	- 'ovito_tool.py': Internal module containing Ovito interfacing
	- 'snapshot.py': Internal module implementing Snapshot class
	- 'snapshots.py': Internal module implementing Snapshots class
	- 'sources.py': Internal module for parsing LAMMPS dump file format
	- 'visualize.py': Internal module implementing Ovito view window

## Basic Usage
The documentation here is not exhaustive, but rather an overview of the most common features and functions. Refer to the docstrings for complete documentation.

### dump_reader

`dump_reader` implements parsing and manipulation of LAMMPS dump files through its `Snapshot` and `Snapshots` objects. `dump_reader` is mainly intended for users wishing to conduct custom programmatic analyses on LAMMPS dump files. The `Snapshot` and `Snapshots` objects should be your only point of interface with the module, as shown. This module is implemented to minimize RAM usage so that large dump files can be easily manipulated. Per-atom data is only loaded into memory when it is needed.

```python
from dump_reader import Snapshot, Snapshots
```

A `Snapshot` object, as its name suggests, is a snapshot of the system and its atoms. A `Snapshots` object is a container of `Snapshot` objects. A `Snapshots` object has a fixed collection of `Snapshot` objects, which it always owns. To create a `Snapshots` object from a LAMMPS dump file, call the `from_dump` constructor:

```python
snapshots = Snapshots.from_dump("example.dump")
```

`Snapshots` objects can be sliced to obtain the underlying `Snapshot` objects as tuples

```python
snapshot_object = snapshots[0]
snapshot_objects = snapshots[0:10]
```

Further, a new `Snapshots` object can be sliced:

```python
reversed_snapshots = snapshots.new[::-1]
```

`Snapshots` can be summed with a Snapshot object or another Snapshots object

```python
snapshots_sum = snapshots + snapshots

snapshot_sum = snapshots + snapshots[0]
```

The `Snapshot` object collects relevant data, including the timestep and box information, which may be edited. However, per-atom data cannot be directly edited. Rather, the snapshot must be converted to another form (e.g. atomman `System`) and then converted back.

```python
snapshot.timestep = 10
snapshot.box.bounds[0] = (-10, 10)
```

This data is conglomerated by `Snapshots`, so it may be edited on the `Snapshots` level.

```python
snapshots.timesteps = 0 # Assign 0 to all timesteps
snapshots.boxes.bounds *= 2
```

`Snapshot` objects implement a dict-like object called `custom` where custom global properties can be defined and will be stored and read from LAMMPS dump files. `custom` will contain any custom global data from dump files read in. New custom data should be created at the `Snapshots` level:

```python
snapshots.custom["my_property"] = 0 # Initialize property as 0 for all snapshots

# The following are equivalent:
snapshots[0].custom = 1
#
snapshots.custom["my_property"][0] = 1
```

`Snapshot` objects can be visualized in an interactive window if the Ovito module is installed:

```python
snapshot.render()
```

A `Snapshot` object can be converted to an Atomman `System` object. Note that Atomman `System` objects do not track timestep or custom data.

```python
system = snapshot.to_atomman()
```

To convert an Atomman `System` object to a `Snapshot`:

```python
new_snapshot = Snapshot.from_atomman(system, timestep = 0, custom = None)
```

Finally, `Snapshots` objects can be written to a LAMMPS file:

```python
snapshots.write_dump("MyPath.dump")
```

## Creator
Joshua Kempfert (joshuakempfert@gmail.com)

## Additional Info
- https://www.ovito.org/
- https://www.ctcms.nist.gov/potentials/atomman/
- https://docs.lammps.org/Manual.html

