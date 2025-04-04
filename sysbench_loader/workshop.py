"""Fill in a module description here"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_workshop.ipynb.

# %% auto 0
__all__ = ['wiener_hammerstein', 'silverbox', 'cascaded_tanks', 'emps', 'noisy_wh', 'ced']

# %% ../nbs/01_workshop.ipynb 2
from .core import *
import nonlinear_benchmarks
from nonlinear_benchmarks.utilities import Input_output_data
from pathlib import Path
import shutil

# %% ../nbs/01_workshop.ipynb 8
def wiener_hammerstein(
        save_path: Path, #directory the files are written to, created if it does not exist
        force_download: bool = False, # force download the dataset
        save_train_valid: bool = False, # save unsplitted train and valid datasets in 'train_valid' subdirectory
        split_idx: int = 80_000 # split index for train and valid datasets
):
    train_val, test = nonlinear_benchmarks.WienerHammerBenchMark(force_download=force_download)
    train = train_val[:split_idx]
    valid = train_val[split_idx:]

    dataset_to_hdf5(train,valid,test,save_path,train_valid=(train_val if save_train_valid else None))

# %% ../nbs/01_workshop.ipynb 12
def silverbox(
        save_path: Path, #directory the files are written to, created if it does not exist
        force_download: bool = False, # force download the dataset
        save_train_valid: bool = False, # save unsplitted train and valid datasets in 'train_valid' subdirectory
        split_idx: int = 50_000 # split index for train and valid datasets
):
    train_val, test = nonlinear_benchmarks.Silverbox(force_download=force_download)
    train = train_val[:split_idx]
    valid = train_val[split_idx:]

    dataset_to_hdf5(train,valid,test,save_path,train_valid=(train_val if save_train_valid else None))

# %% ../nbs/01_workshop.ipynb 16
def cascaded_tanks(
        save_path: Path, #directory the files are written to, created if it does not exist
        force_download: bool = False, # force download the dataset
        save_train_valid: bool = False, # save unsplitted train and valid datasets in 'train_valid' subdirectory
        split_idx: int = 160 # split index for train and valid datasets
):
    train_val, test = nonlinear_benchmarks.Cascaded_Tanks(force_download=force_download)
    train = train_val[split_idx:]
    valid = train_val[:split_idx]

    dataset_to_hdf5(train,valid,test,save_path,train_valid=(train_val if save_train_valid else None))

# %% ../nbs/01_workshop.ipynb 20
def emps(
        save_path: Path, #directory the files are written to, created if it does not exist
        force_download: bool = False, # force download the dataset
        save_train_valid: bool = False, # save unsplitted train and valid datasets in 'train_valid' subdirectory
        split_idx: int = 18_000 # split index for train and valid datasets
):
    train_val, test = nonlinear_benchmarks.EMPS(force_download=force_download)
    train = train_val[:split_idx]
    valid = train_val[split_idx:]

    dataset_to_hdf5(train,valid,test,save_path,train_valid=(train_val if save_train_valid else None))

# %% ../nbs/01_workshop.ipynb 23
from scipy.io import loadmat
def noisy_wh(
        save_path: Path, #directory the files are written to, created if it does not exist
        force_download: bool = False, # force download the dataset
        save_train_valid: bool = False # save unsplitted train and valid datasets in 'train_valid' subdirectory
):
    'the wiener hammerstein dataset with process noise'

    #extract raw .mat files, to preserve filenames necessary for train, valid split
    matfiles = nonlinear_benchmarks.not_splitted_benchmarks.WienerHammerstein_Process_Noise(data_file_locations=True,train_test_split=False,force_download=force_download)

    for file in matfiles:
        f_path = Path(file)
        save_path = Path(save_path)

        if 'Test' in f_path.stem:
            hdf_path = save_path / 'test'
        elif 'Combined' in f_path.stem:
            hdf_path = save_path / 'valid'
        else:
            hdf_path = save_path / 'train'

        out = loadmat(f_path)
        _,u,y,fs = out['dataMeas'][0,0]
        fs = fs[0,0]
        for idx,(ui,yi) in enumerate(zip(u.T,y.T)):
            iodata = Input_output_data(u=ui,y=yi, sampling_time=1/fs)
            fname = f'{f_path.stem}_{idx+1}'
            iodata_to_hdf5(iodata,hdf_path,fname)
    if save_train_valid:
        #copy train and valid files to train_valid directory
        for d in ['train','valid']:
            for f in (Path(save_path)/d).glob('*.hdf5') :
                shutil.copy2(f, (p:=Path(save_path)/'train_valid').mkdir(exist_ok=True) or p)


# %% ../nbs/01_workshop.ipynb 31
def ced(
        save_path: Path, #directory the files are written to, created if it does not exist
        force_download: bool = False, # force download the dataset
        save_train_valid: bool = False, # save unsplitted train and valid datasets in 'train_valid' subdirectory
        split_idx: int = 300 # split index for train and valid datasets
):
    train_val, test = nonlinear_benchmarks.CED(force_download=force_download,always_return_tuples_of_datasets=True)
    train = tuple(x[:split_idx] for x in train_val)
    valid = tuple(x[split_idx:] for x in train_val)

    dataset_to_hdf5(train,valid,test,save_path,train_valid=(train_val if save_train_valid else None))
