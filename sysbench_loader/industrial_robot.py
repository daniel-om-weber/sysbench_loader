# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/02_industrial_robot.ipynb.

# %% auto 0
__all__ = ['industrial_robot']

# %% ../nbs/02_industrial_robot.ipynb 2
from .core import unrar_download, write_dataset,write_array
from nonlinear_benchmarks.utilities import cashed_download
from pathlib import Path
import os
import h5py
import numpy as np

# %% ../nbs/02_industrial_robot.ipynb 4
import scipy.io as sio

def industrial_robot(
        save_path: Path #directory the files are written to, created if it does not exist
):
    save_path = save_path / 'industrial_robot'
    url_robot = "https://fdm-fallback.uni-kl.de/TUK/FB/MV/WSKL/0001/Robot_Identification_Benchmark_Without_Raw_Data.rar"
    # unrar_download(url_robot,tmp_dir)

    tmp_dir = cashed_download(url_robot,'Industrial_robot')
    tmp_dir = Path(tmp_dir)

    train_valid_split = 0.8

    path_forward = tmp_dir / "forward_identification_without_raw_data.mat"
    path_inverse = tmp_dir / "inverse_identification_without_raw_data.mat"

    fs = 10  # Hz
    
    # Convert the matlab sequences to hdf5 files
    for idx, path in enumerate([path_forward, path_inverse]):
        if idx == 0:
            store_path = save_path / 'forward'
        else:
            store_path = save_path / 'inverse'
        os.makedirs(store_path, exist_ok=True)
             
        mf = sio.loadmat(path)
        for mode in ['train', 'test']:
            if mode == 'test':
                with h5py.File(store_path / f'test.hdf5', 'w') as f:
                    write_dataset(f, 'dt', np.ones_like(mf[f'time_{mode}'][0]) / fs)
                    write_array(f, 'u', mf[f'u_{mode}'].T)
                    write_array(f, 'y', mf[f'y_{mode}'].T)
            else:
                with h5py.File(store_path / f'train.hdf5', 'w') as train_f, \
                    h5py.File(store_path / f'valid.hdf5', 'w') as valid_f:
                        dt = np.ones_like(mf[f'time_{mode}'][0]) / fs
                        total_entries = len(dt)
                        split_index = int(total_entries * train_valid_split)

                        write_dataset(train_f, 'dt', dt[:split_index])
                        write_array(train_f, 'u', mf[f'u_{mode}'][:,:split_index].T)
                        write_array(train_f, 'y', mf[f'y_{mode}'][:,:split_index].T)
                        
                        write_dataset(valid_f, 'dt', dt[split_index:])
                        write_array(valid_f, 'u', mf[f'u_{mode}'][:,split_index:].T)
                        write_array(valid_f, 'y', mf[f'y_{mode}'][:,split_index:].T)
    
