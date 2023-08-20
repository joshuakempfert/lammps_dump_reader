# -*- coding: utf-8 -*-
"""
Tools for reading and manipulating dump files

Contents:
    Snapshot - Class representing a single dump snapshot
    Snapshots - Class representing a collection of dump snapshots, usually originating from a
                LAMMPS dump file
                

Modules do not need to be directly accessed
"""

from .snapshots import Snapshots

from .snapshot import Snapshot
