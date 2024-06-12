# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/03_ship.ipynb.

# %% auto 0
__all__ = ['ship']

# %% ../nbs/03_ship.ipynb 2
from nonlinear_benchmarks.utilities import get_tmp_benchmark_directory
from pathlib import Path
import os
import h5py
import numpy as np
from easyDataverse import Dataverse
import pandas as pd
import shutil

# %% ../nbs/03_ship.ipynb 3
def ship(
        save_path: Path, #directory the files are written to, created if it does not exist
        remove_download = True
):
    save_path = Path(save_path)
    download_dir = Path(get_tmp_benchmark_directory()) / 'Ship'

    dataverse = Dataverse('https://darus.uni-stuttgart.de/')
    dataverse.load_dataset(
        pid='doi:10.18419/darus-2905',
        filedir=download_dir,
    )

    #str to Path to be plattform independent
    structure_mapping = {
        Path('patrol_ship_routine/processed/train'): 'train',
        Path('patrol_ship_routine/processed/validation'): 'valid',
        Path('patrol_ship_routine/processed/test'): 'test',
        Path('patrol_ship_ood/processed/test'): 'test_ood'
    }

    # Ensure desired directories exist
    for subdir in structure_mapping.values():
        os.makedirs(os.path.join(save_path, subdir), exist_ok=True)

    def convert_tab_to_hdf5(tab_path, hdf5_path):
        df = pd.read_csv(tab_path, sep='\t')
        with h5py.File(hdf5_path, 'w') as hdf:
            for column in df.columns:
                data = df[column].astype(np.float32).values
                hdf.create_dataset(column, data=data, dtype='f4')

    # Walk through the current directory structure and process files
    for subdir, dirs, files in os.walk(download_dir):
        for file in files:
            if file.endswith('.tab'):
                current_file_path = os.path.join(subdir, file)
                
                # Determine the relative path
                relative_subdir = Path(os.path.relpath(subdir, download_dir))
                
                # Find the corresponding desired subdir
                if relative_subdir in structure_mapping:
                    desired_subdir = structure_mapping[relative_subdir]
                    
                    # Construct desired file paths
                    base_filename = file.replace('.tab', '')
                    desired_hdf5_path = os.path.join(save_path, desired_subdir, base_filename + '.hdf5')
                    
                    convert_tab_to_hdf5(current_file_path, desired_hdf5_path)

    #remove downloaded files
    if remove_download:
        shutil.rmtree(download_dir)
