.. robust_speckle_tracking documentation master file, created by
   sphinx-quickstart on Fri Oct 30 16:00:08 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

rst
===

rst is a Python library for wavefront metrology and sample imaging
based on ptychographic speckle tracking algorithm. This project
takes over Andrew Morgan's `speckle_tracking`_ project
as an improved version aiming to add robustness to the optimisation
algorithm in the case of the high noise present in the measured data.

.. _speckle_tracking: https://github.com/andyofmelbourne/speckle-tracking

The library is written in Python 3 and uses a C++ back endwritten
in `Cython`_. The library is capable to perform the Speckle Tracking
algorithm, which yields an unabberated profile of the sample and the wavefront
of the lens. Also it contains a set of auxiliary data processing
routines, such as bad pixel masking, defocus sweep scan, wavefront
reconstruction, phase model fitting, etc. All of them are listed in
:class:`STData`.

st_sim
======

The library also contains the Speckle Tracking Simulation (st_sim) package.
st_sim is capable to simulate one-dimensional speckle tracking scans
based on the Fresnel Diffraction theory.

.. _Cython: https://cython.org


Python Reference
================

.. toctree::
   :maxdepth: 4
   :caption: Contents:

   reference/api



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`