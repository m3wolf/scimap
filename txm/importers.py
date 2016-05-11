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
# along with Scimap. If not, see <http://www.gnu.org/licenses/>.

import os
import h5py
import re
from time import time
from collections import namedtuple

from tqdm import tqdm
import pandas as pd
import numpy as np
from PIL import Image

from .xradia import XRMFile, decode_ssrl_params
from .xanes_frameset import XanesFrameset, energy_key
from .frame import TXMFrame
from utilities import prog
import exceptions


format_classes = {
    '.xrm': XRMFile
}


def _prepare_hdf_group(filename: str, groupname: str, dirname: str):
    """Check the filenames and create an hdf file as needed. Will
    overwrite the group if it already exists.

    Returns: HDFFile

    Arguments
    ---------

    - filename : name of the requested hdf file, may be None if not
      provided, in which case the filename will be generated
      automatically based on `dirname`.

    - groupname : Requested groupname for these data.

    - dirname : Used to derive a default filename if None is passed
      for `filename` attribute.
    """
    # Get default filename and groupname if necessary
    if filename is None:
        real_name = os.path.abspath(dirname)
        new_filename = os.path.split(real_name)[1]
        hdf_filename = "{basename}-results.h5".format(basename=new_filename)
    else:
        hdf_filename = filename
    if groupname is None:
        groupname = os.path.split(os.path.abspath(dirname))[1]
    # Open actual file
    hdf_file = h5py.File(hdf_filename)
    # Alert the user that we're overwriting this group
    if groupname in hdf_file.keys():
        msg = 'Group "{groupname}" exists. Overwriting.'
        print(msg.format(groupname=groupname))
        del hdf_file[groupname]
        # msg += " Try using the `hdf_groupname` argument"
        # e = exceptions.CreateGroupError(msg.format(groupname=groupname))
        # raise e
    new_group = hdf_file.create_group(groupname)
    # User feedback
    if not prog.quiet:
        print('Saving to HDF5 file {file} in group {group}'.format(
            file=hdf_filename,
            group=groupname)
        )
    return new_group


def _average_frames(*frames):
    """Accept several frames and return the first frame with new image
    data. Assumes metadata from first frame in list."""
    new_image = np.zeros_like(frames[0].image_data(), dtype=np.float)
    # Sum all images
    for frame in frames:
        new_image += frame.image_data()
    # Divide to get average
    new_image = new_image / len(frames)
    # Return average data as a txm frame
    new_frame = frames[0]
    new_frame.image_data = new_image
    return new_frame


def import_txm_framesets(*args, **kwargs):
    msg = "This function is ambiguous. Choose from the more specific importers."
    raise NotImplementedError(msg)


def import_ptychography_frameset(directory: str,
                                 hdf_filename=None, hdf_groupname=None):
    """Import a set of images as a new frameset for generating
    ptychography chemical maps based on data collected at ALS beamline
    5.3.2.1

    Arguments
    ---------

    - results_dir : Directory where to look for results. It should
    contain a subdirectory named "tiffs" and a file named
    "energies.txt"

    - hdf_filename : HDF File used to store computed results. If
      omitted, the `directory` basename is used

    - hdf_groupname : String to use for the hdf group of this
    dataset. If omitted or None, the `directory` basename is
    used. Raises an exception if the group exists.
    """
    CURRENT_VERSION = "0.2" # Let's file loaders deal with changes to storage
    # Prepare some filesystem information
    tiff_dir = os.path.join(directory, "tiffs")
    modulus_dir = os.path.join(tiff_dir, "modulus")
    stxm_dir = os.path.join(tiff_dir, "modulus")
    # Prepare the HDF5 file and metadata
    hdf_group = _prepare_hdf_group(filename=hdf_filename,
                                   groupname=hdf_groupname,
                                   dirname=directory)
    hdf_group.attrs["scimap_version"] = CURRENT_VERSION
    hdf_group.attrs["technique"] = "ptychography STXM"
    hdf_group.attrs["beamline"] = "ALS 5.3.2.1"
    hdf_group.attrs["original_directory"] = os.path.abspath(directory)
    # Prepare groups for data
    imported = hdf_group.create_group("imported")
    hdf_group.attrs["active_group"] = "imported"
    imported_group = imported.name
    hdf_group["imported"].attrs["level"] = 0
    hdf_group["imported"].attrs["parent"] = ""
    hdf_group["imported"].attrs["default_representation"] = "modulus"
    file_re = re.compile("projection_modulus_(?P<energy>\d+\.\d+)\.tif")
    for filename in os.listdir(modulus_dir):
        # (assumes each image type has the same set of energies)
        # Extract energy from filename
        match = file_re.match(filename)
        if match is None:
            msg = "Could not read energy from filename {}".format(filename)
            raise exceptions.FilenameParseError(msg)
        energy_str = match.groupdict()['energy']
        # All dataset names will be the energy with two decimal places
        energy_set = imported.create_group(energy_key.format(float(energy_str)))
        energy_set.attrs['energy'] = float(energy_str)
        energy_set.attrs['approximate_energy'] = round(float(energy_str), 2)
        energy_set.attrs['pixel_size_value'] = 4.17
        energy_set.attrs['pixel_size_unit'] = "nm"
        def add_files(name, template="projection_{name}_{energy}.tif"):
            # Import modulus (total value)
            filename = template.format(name=name, energy=energy_str)
            filepath = os.path.join(tiff_dir, name, filename)
            data = Image.open(filepath)
            energy_set.create_dataset(name, data=data, chunks=True)
        representations = ['modulus', 'phase', 'complex', 'intensity']
        [add_files(name) for name in representations]
        add_files("stxm", template="stxm_{energy}.tif")
    # Create the frameset object
    hdf_filename = hdf_group.file.filename
    hdf_groupname = hdf_group.name
    hdf_group.file.close()
    frameset = XanesFrameset(filename=hdf_filename,
                             groupname=hdf_groupname,
                             edge=None)
    frameset.latest_group = imported_group


_SsrlResponse = namedtuple("_SsrlResponse", ("data", "starttime", "endtime"))

def _average_ssrl_files(files):
    starttimes = []
    endtimes = []
    arrays = []
    # Average sample frames
    for filename in files:
        name, extension = os.path.splitext(filename)
        Importer = format_classes[extension]
        with Importer(filename=filename, flavor="ssrl") as txmfile:
            starttimes.append(txmfile.starttime())
            endtimes.append(txmfile.endtime())
            # Append to the running total array (create if first frame)
            arrays.append(txmfile.image_data())
    # Prepare the result tuple
    response = _SsrlResponse(
        data=np.mean(arrays, axis=0),
        starttime=min(starttimes),
        endtime=max(endtimes)
    )
    return response


def import_ssrl_frameset(directory, hdf_filename=None):
    """Import all files in the given directory collected at SSRL beamline
    6-2c and process into framesets. Images are assumed to full-field
    transmission X-ray micrographs and repetitions will be averaged.
    """
    # Prepare list of dataframes to be imported
    samples = {}
    references = {}
    start_time = time()
    total_files = 0 # Counter for progress meter
    curr_file = 0
    # Prepare a dictionary of samples, each sample is a dictionary of
    # energies, which contains a list of filenames to be imported
    for filename in os.listdir(directory):
        # Make sure it's a file
        fullpath = os.path.join(directory, filename)
        if os.path.isfile(fullpath):
            # Queue the file for import if the extension is known
            name, extension = os.path.splitext(filename)
            if extension in format_classes.keys():
                metadata = decode_ssrl_params(filename)
                framesetname = metadata['sample_name'] + metadata['position_name']
                if metadata['is_background']:
                    root = references
                else:
                    root = samples
                energies = root.get(framesetname, {})
                replicates = energies.get(metadata['energy'], [])
                # Update the stored tree
                root[framesetname] = energies
                replicates.append(fullpath)
                energies[metadata['energy']] = replicates
                total_files += 1
    # Check that in the ssrl flavor, each sample has a reference set
    if not samples.keys() == references.keys():
        msg = "SSRL data should have 1-to-1 sample to reference: {} and {}"
        raise exceptions.DataFormatError(msg.format(list(samples.keys()),
                                                    list(references.keys())))
    # Go through each sample and import
    for sample_name, sample in samples.items():
        sample_group = _prepare_hdf_group(filename=hdf_filename,
                                          groupname=sample_name,
                                          dirname=directory)
        imported = sample_group.create_group("imported")
        imported.attrs['default_representation'] = 'image_data'
        imported.attrs['parent'] = ""
        reference = sample_group.create_group("reference")
        reference.attrs['default_representation'] = 'image_data'
        reference.attrs['parent'] = ""
        absorbance = sample_group.create_group("reference_corrected")
        absorbance.attrs['default_representation'] = 'image_data'
        absorbance.attrs['parent'] = imported.name
        sample_group.attrs['latest_group'] = absorbance.name
        # Average data for each energy
        for energy in sample:
            intensity = _average_ssrl_files(sample[energy])
            key = energy_key.format(float(energy))
            intensity_group = imported.create_group(key)
            intensity_group.create_dataset(name="image_data", data=intensity.data)
            # Set some metadata attributes
            intensity_group.attrs['starttime'] = intensity.starttime.isoformat()
            intensity_group.attrs['endtime'] = intensity.endtime.isoformat()
            file1 = sample[energy][0]
            name, extension = os.path.splitext(file1)
            Importer = format_classes[extension]
            with Importer(file1, flavor='ssrl') as first_file:
                intensity_group.attrs['pixel_size_value'] = first_file.um_per_pixel()
                intensity_group.attrs['pixel_size_unit'] = 'um'
                actual_energy = first_file.energy()
                intensity_group.attrs['energy'] = actual_energy
                intensity_group.attrs['approximate_energy'] = round(actual_energy, 1)
                intensity_group.attrs['sample_position'] = first_file.sample_position()
                intensity_group.attrs['original_filename'] = file1
            # Increment counter
            curr_file += len(sample[energy])
            # Display progress meter
            if not prog.quiet:
                status = tqdm.format_meter(n=curr_file,
                                           total=total_files,
                                           elapsed=time() - start_time,
                                           prefix="Importing frames: ")
                print("\r", status, end='')
            # Average reference frames
            ref = _average_ssrl_files(references[sample_name][energy])
            ref_group = reference.create_group(key)
            ref_group.create_dataset(name="image_data", data=ref.data)
            # Apply reference correction to get absorbance data
            abs_data = np.log(ref.data / intensity.data)
            abs_group = absorbance.create_group(key)
            abs_group.create_dataset(name="image_data", data=abs_data)
            # Copy attrs
            for key in intensity_group.attrs.keys():
                ref_group.attrs[key] = intensity_group.attrs[key]
                abs_group.attrs[key] = intensity_group.attrs[key]
            # Increment counter
            curr_file += len(references[sample_name][energy])
            # Display progress meter
            if not prog.quiet:
                status = tqdm.format_meter(n=curr_file,
                                           total=total_files,
                                           elapsed=time() - start_time,
                                           prefix="Importing frames: ")
                print("\r", status, end='')
        sample_group.file.close()
    if not prog.quiet:
        print()  # Blank line to avoid over-writing status message
        print("Remember to run XanesFrameset.correct_magnification()")


def import_aps_8BM_frameset(directory, hdf_filename=None):
    raise NotImplementedError
    # # Remove dead or hot pixels
    # if flavor in ['aps']:
    #     sigma = 9
    #     for fs in frameset_list:
    #         for frame in prog(fs, 'Removing pixels beyond {}σ'.format(sigma)):
    #             frame.remove_outliers(sigma=sigma)
    # return frameset_list
