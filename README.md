# lammps_utility
Python For Engineers: Project

## Description
This package automates common data analysis tasks for the molecular dynamics software LAMMPS. Namely, this package offers a parser for reading LAMMPS therodynamic data from log files, a dump file parser/manipulator, and an interactive GUI implementing basic plotting features. 


## Download Instructions

1) Download directory
2) Ensure all Packaged Files are in the same working directory as specified below
3) Create environment using 'environment.yaml' file. Note: This environment is for Windows-only.
	`conda env create --file environment.yml`

4) Open 'example.ipynb'. Utilize the Jupyter Notebook as an instructional on how to use the package.

## Files 
- 'lammps_utility': lammps_utility python package
 	- 'thermo_reader.py': Package for extracting information from .log file and plotting to Plotly
 	- 'data_gui.py': Program for generating GUI with plotting features
 	- 'units_info.yaml': Contains LAMMPS unit style information for auto-detecting units in thermo_reader
	- 'dump_reader': Package for parsing and manipulating LAMMPS dump files
		- 'box.py': Internal module implementing Box class
		- 'common.py': Internal module containing some utilities
		- 'ovito_tool.py': Internal module containing Ovito interfacing
		- 'snapshot.py': Internal module implementing Snapshot class
		- 'snapshots.py': Internal module implementing Snapshots class
		- 'sources.py': Internal module for parsing LAMMPS dump file format
		- 'visualize.py': Internal module implementing Ovito view window
	- Subfolder: 'GUI_figures': Includes Images Displayed in GUI
		- 'background.png': GUI Background Image
		- 'Happy Holidays.png': Initial Image Displayed on GUI Main Screen
		- 'logo.gif': GIF of LAMMPS logo
## Basic Usage
The documentation here is not exhaustive, but rather an overview of the most common features and functions. Refer to the docstrings for complete documentation.

### dump_reader

`dump_reader` implements parsing and manipulation of LAMMPS dump files through its `Snapshot` and `Snapshots` objects. `dump_reader` is mainly intended for users wishing to conduct custom programmatic analyses on LAMMPS dump files. The `Snapshot` and `Snapshots` objects should be your only point of interface with the module, as shown. This module is implemented to minimize RAM usage so that large dump files can be easily manipulated. Per-atom data is only loaded into memory when it is needed.

```python
from lammps_utility.dump_reader import Snapshot, Snapshots
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

## thermo_reader

`thermo_reader` parses YAML thermodynamic tables from LAMMPS log files and offers interactive plotting functionality using `plotly`. LAMMPS thermodynamic tables are not in YAML format by default. See LAMMPS [thermo_style](https://docs.lammps.org/thermo_style.html) and [thermo_modify](https://docs.lammps.org/thermo_modify.html) documentation for instructions on converting your output format to YAML.

Also, the use of the LAMMPS stdout file is preferable to the log file because the stdout file provides unit style information with runs. The script will function with either, but the unit style information allows `thermo_reader` to label units automatically.

```python
import lammps_utility.thermo_reader
```

To parse your file, call:

```python
dataframes = thermo_reader.parse_log_file("LogFilePath.log")
```

This returns a one-indexed `dict` of `Pandas` DataFrames corresponding to the thermodynamic tables for each run. Additional information is stored in the dataframes `attrs` `dict` if it was detected, i.e.:

```python
dataframes[0].attrs
```

An interactive plotting function is also included. Using the previous results:

```python
thermo_reader.plot_log_data(dataframes, index = 1, y = "Press", x = None, write_path = None):
```

where `index` is the key of the run. This will create an interactive `plotly` graph in your browser, with the units auto-populated if they are available (see discussion above).



## data_gui

`data_gui` provides a straightforward interface for plotting properties with respect to timesteps, given either **.log** or **.dump** files. It is noted, upon plotting specified parameters, an interactive `plotly` graph will be displayed on a local web browser as well as the graphical interface.

```python
import lammps_utility.data_gui
```

To open the GUI, call:

```python
lammps_utility.data_gui.launch()
```

Alternatively, `data_gui.py` can be run directly through a command-line or IDE.

An interactive display will be present, allowing users to select two options:
1) **Thermo. Plot**: plot thermodynamic properties from an associated **.log** file

2) **Dump Plot**: plotting per-atom properties from `Snapshot`objects from an associated **.dump** file


## Creators
Joshua Kempfert, Alan Smith, Matthew Nguyen

## Additional Info
- https://www.ovito.org/
- https://www.ctcms.nist.gov/potentials/atomman/
- https://docs.lammps.org/Manual.html

