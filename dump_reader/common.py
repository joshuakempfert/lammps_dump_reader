# -*- coding: utf-8 -*-
"""
Some common methods and classes shared throughout dump_reader
"""

def has_no_length(x):
    """
    Used to test whether x can be considered array-like. In this implementation, strings are not
    considered array-like
    """
    
    try:
        # Test if x is string-like
        if (x == str(x)) is True:
            return True
        
        len(x)        
        
        return False
    except TypeError:
        return True

def is_single_value(x):
    """
    Tests whether x can be considered a single-value, which occurs if x has a length <=1 or
    or has no defined length"""
    ""
    
    try:
        # If len is defined, this will return True if x has a length less than or equal to one
        return len(x) <= 1
    except TypeError:
        # If len is not defined, x is a single value
        return True

class readonly:
    """
    Class descriptor which allows property to be set only once (presumably during __init__).
    """
    
    def __set_name__(self, owner, name):
        self.public_name = name
        self.private_name = '_' + name

    def __get__(self, instance, owner):        
        return getattr(instance, self.private_name)
    
    def __set__(self, instance, value):
        if getattr(instance, self.private_name, None) is None:
            setattr(instance, self.private_name, value)
        else:
            raise ValueError(f"Attempt to set readonly property {self.public_name}")
