#! /usr/bin/env python

from distutils.core import setup, Extension

shared_module = Extension('_haversine', sources = ['haversine_wrap.c', \
                                             'haversine.c'],)
setup (name = 'haversine', version = '1.0', author = 'Cameron', description = \
       "Haversine and Ellipse Functions", \
       ext_modules = [shared_module], py_modules = ['haversine'],)
