"""Fill in a module description here"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_core.ipynb.

# %% auto 0
__all__ = ['write_dataset', 'write_array', 'iodata_to_hdf5', 'dataset_to_hdf5', 'unzip_download', 'unrar_download', 'download']

# %% ../nbs/00_core.ipynb 3
from nonlinear_benchmarks import *
from pathlib import Path
import numpy as np
import h5py
import os

# %% ../nbs/00_core.ipynb 9
def write_dataset(group, #opened hdf5 group to write the dataset, can be a file or group
         ds_name:str, #name of the new dataset
         data: np.array, #data to write to the dataset
         dtype='f4', #datatype, the data will be converted to
         chunks=None #chunking of the hdf5 file, enables faster reading and writing of small parts
         ):
    group.create_dataset(ds_name, data=data, dtype=dtype, chunks=chunks)

# %% ../nbs/00_core.ipynb 11
def write_array(group, #opened hdf5 group to write the dataset, can be a file or group
                ds_name:str, #name of the new dataset
                data: np.array, #data to write to the dataset
                dtype='f4', #datatype, the data will be converted to
                chunks=None #chunking of the hdf5 file, enables faster reading and writing of small parts
                ) -> None:
    'Writes a 2d numpy array rowwise to a hdf5 file.'
    for i in range(data.shape[1]):
        write_dataset(group, f'{ds_name}{i}', data[:,i], dtype, chunks)

# %% ../nbs/00_core.ipynb 13
def iodata_to_hdf5(iodata:Input_output_data, # data to save to file
            hdf_dir:Path, # Export directory for hdf5 files
            f_name:str = None # name of hdf5 file without '.hdf5' ending
            ):
    data_2d = iodata.atleast_2d()
    u,y = data_2d.u, data_2d.y
    
    os.makedirs(hdf_dir,exist_ok=True)
    if f_name is None: f_name = iodata.name
    
    hdf_path = Path(hdf_dir) / f'{f_name}.hdf5'.replace(" ", "_")
    with h5py.File(hdf_path,'w') as f:
        write_array(f,'u',u)
        write_array(f,'y',y)
        
        # Save sampling_rate and init_window_size as attributes
        if iodata.sampling_time is not None:
            f.attrs['fs'] = 1/iodata.sampling_time
        if iodata.state_initialization_window_length is not None:
            f.attrs['init_sz'] = iodata.state_initialization_window_length

    return hdf_path 

# %% ../nbs/00_core.ipynb 20
def dataset_to_hdf5(train:tuple, #tuple of Input_output_data for training
                    valid:tuple,#tuple of Input_output_data for validation
                    test:tuple,#tuple of Input_output_data for test
                    save_path: Path, #directory the files are written to, created if it does not exist
                    train_valid: tuple = None # optional tuple of unsplit Input_output_data for training and validation
                    ):
    'Save a dataset consisting of training, validation, and test set in hdf5 format in seperate subdirectories'
    save_path = Path(save_path)
    
    dict_data = {'train':train,
                 'valid':valid,
                 'test':test,
                 'train_valid':train_valid}
    for subset,ds_entries in dict_data.items():
        if ds_entries is None: continue
        if isinstance(ds_entries,tuple):
            if not isinstance(ds_entries[0],Input_output_data): raise ValueError(f'Data has to be stored in tuples of Input_output_data. Got {type(ds_entries[0])}')
        else:
            if not isinstance(ds_entries,Input_output_data): raise ValueError(f'Data has to be stored in Input_output_data. Got {type(ds_entries)}')
            dict_data[subset] = (ds_entries,)

    os.makedirs(save_path,exist_ok=True)

    for subset,ds_entries in dict_data.items():
        if ds_entries is None: continue
        for idx,iodata in enumerate(ds_entries):
            iodata_to_hdf5(iodata,save_path / subset,f'{subset}_{idx}')

# %% ../nbs/00_core.ipynb 24
import requests,io,os
import zipfile,rarfile

# %% ../nbs/00_core.ipynb 25
def unzip_download(url:str, #url to file to download
                   extract_dir = '.' #directory the archive is extracted to
                   ):
    'downloads a zip archive to ram and extracts it'
    response = requests.get(url)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        zip_ref.extractall(extract_dir)

# %% ../nbs/00_core.ipynb 26
def unrar_download(url:str, #url to file to download
                   extract_dir = '.' #directory the archive is extracted to
                   ):
    'downloads a rar archive to ram and extracts it'
    response = requests.get(url)
    with rarfile.RarFile(io.BytesIO(response.content)) as zip_ref:
        zip_ref.extractall(extract_dir)

# %% ../nbs/00_core.ipynb 27
def download(url:str, #url to file to download
             target_dir = '.'
             ):
    fname = Path(url).name
    if os.path.isfile(fname): return
    response = requests.get(url)
    p_name = Path(target_dir).joinpath(fname)
    with open(p_name, "wb") as file:
        file.write(response.content)
    return p_name
