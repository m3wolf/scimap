# -*- coding: utf-8 -*-
#
# Copyright © 2016 Mark Wolf
#
# This file is part of scimap.
#
# Scimap is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Scimap is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Scimap.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import os

import numpy as np

from scimap import XRDScan

TESTDIR = os.path.join(os.path.dirname(__file__), "test-data-xrd")
COR_BRML = os.path.join(TESTDIR, 'corundum.brml')

class XRDScanTest(unittest.TestCase):
    def test_init_wavelength(self):
        scan = XRDScan()
        self.assertAlmostEqual(scan.wavelength, 1.54187, places=4)
        # Try supplying a wavelength explicitly
        scan = XRDScan(wavelength=1.90)
        self.assertEqual(scan.wavelength, 1.90)
    
    def test_get_scattering_lengths(self):
        # Check for a .brml file
        scan = XRDScan(filename=os.path.join(TESTDIR, 'corundum.brml'))
        q = scan.scattering_lengths
        self.assertEqual(q.shape, (6851,))
        # Check for a .plt file
        scan = XRDScan(filename=os.path.join(TESTDIR, 'LMO-sample-data.plt'))
        q = scan.scattering_lengths
    
    def test_diffractogram(self):
        scan = XRDScan(filename=COR_BRML)
        df = scan.diffractogram
        # Check that the diffractogram loads 2θ and intensities
        np.testing.assert_equal(df.index, scan.two_theta)
