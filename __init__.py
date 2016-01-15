# -*- coding: utf-8 -*-

# Make sure this directory is in python path for imports
import sys
import os
sys.path.append(os.path.dirname(__file__))

import default_units
from electrochem.electrochem_units import *

from xrd.peak import XRDPeak
# from xrdpeak import PeakFit

from plots import (new_axes, big_axes, dual_axes, plot_scans, xrd_axes,
                   plot_txm_intermediates)

import filters

from utilities import xycoord

from refinement import fullprof

from xrd.unitcell import CubicUnitCell, HexagonalUnitCell, TetragonalUnitCell
from xrd import standards, lmo, bruker
from xrd.lmo import LMOPlateauMap
from xrd.reflection import Reflection
from xrd.scan import XRDScan, align_scans
from xrd.map import XRDMap

from mapping.coordinates import Cube
from mapping.map import Map, DummyMap, PeakPositionMap, PhaseRatioMap, FwhmMap
from mapping import colormaps

# Electrochemistry methods and classes
from electrochem.electrode import CathodeLaminate, CoinCellElectrode
from electrochem.galvanostatrun import GalvanostatRun
from electrochem.cycle import Cycle
from electrochem.plots import plot_rate_capacities

# X-ray microscopy
from txm.xradia import XRMFile
from txm.importers import import_txm_framesets
from txm.xanes_frameset import XanesFrameset
from txm.frame import TXMFrame, calculate_particle_labels, rebin_image
from txm.edges import k_edges
from txm.plotter import FramesetMoviePlotter
