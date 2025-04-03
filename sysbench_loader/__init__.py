__version__ = "0.0.7"

from sysbench_loader.workshop import *
from sysbench_loader.industrial_robot import *
from sysbench_loader.ship import *
from sysbench_loader.quad_pelican import *
from sysbench_loader.quad_pi import *
from sysbench_loader.broad import *
from pathlib import Path


all_dataset_loader = [
    wiener_hammerstein,
    silverbox,
    cascaded_tanks,
    emps,
    noisy_wh,
    robot_forward,
    robot_inverse,
    ship,
    quad_pelican,
    quad_pi,
    broad
]

def download_all_datasets(save_path):
    'Download all datasets provided by sysbench_loader in subdirectories'
    save_path = Path(save_path)
    for loader in all_dataset_loader:
        loader(save_path / loader.__name__)