# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/05_quadrotor_pi.ipynb.

# %% auto 0
__all__ = ['quad_pi']

# %% ../nbs/05_quadrotor_pi.ipynb 2
from nonlinear_benchmarks.utilities import cashed_download, get_tmp_benchmark_directory
from pathlib import Path
import os
import h5py
import numpy as np
import pandas as pd

import gdown
import bagpy
import glob
import scipy
import shutil
from scipy.signal import butter, lfilter, lfilter_zi

# %% ../nbs/05_quadrotor_pi.ipynb 3
fnames_test = ['ovalz_10',
                'ovalz_4',
                '8z_5',
                '8z_6',
                'line8z_4',
                'wz_12',
                'v_8',
                'vT_5']

fnames_valid = ['oval_5',
                'linez_4',
                '8_5',
                '8_7',
                'w_12'
                'vz_7',
                'v_8']

def get_parent_dir(f_name: str # name of the flight
                  ):
    if f_name in fnames_valid:
        return 'valid'
    elif f_name in fnames_test:
        return 'test'
    else:
        return 'train'

# %% ../nbs/05_quadrotor_pi.ipynb 4
def parseBag(topic, path):
  bag = bagpy.bagreader(path, verbose=False)
  return pd.read_csv(bag.message_by_topic(topic))

def shift(arr):
  if len(arr.shape) == 1:
    arr = arr.reshape((len(arr), 1))
  return np.vstack((np.nan * np.ones(shape=(1, arr.shape[1])), arr[:-1]))

def shiftFilteredSpline(sampled_data, step):
  for k in sampled_data.keys():
    if "filt" in k:
      sampled_data[k] = sampled_data[k][step:]
    else:
      sampled_data[k] = sampled_data[k][:-step]

def differentiate(arr, dt):
  a_dot = (arr - shift(arr)) / dt
  a_dot[0, :] = np.zeros((a_dot.shape[1]))
  return a_dot

def differentiateFivePointStencil(arr, dt):
  a_dot = [
    [np.zeros((arr.shape[1]))],
    [(arr[2] - arr[1]) / dt[1]]
  ]
  for i in range(2, len(arr) - 2):
    a_dot.append([(- arr[i + 2] + 8 * arr[i + 1] - 8 * arr[i - 1] + arr[i - 2]) * (1. / (12 * dt[i]))])
  a_dot.append([(arr[-2] - arr[-3]) / dt[-2]])
  a_dot.append([(arr[-1] - arr[-2]) / dt[-1]])
  return np.concatenate(a_dot, axis=0)

def dropNoise(arr, t, dt):
  drop_indeces = []
  for i in range(1, len(arr)):
    if np.any(abs(arr[i]) - abs(sum(arr[i-4:i])) > 0):
      drop_indeces.append(i)
  return np.delete(arr, drop_indeces, axis=0), np.delete(t, drop_indeces, axis=0), np.delete(dt, drop_indeces, axis=0)

def applySavitzkyGolayFilter(arr, window_length, poly_order):
  return np.array([savitzkyGolayFilter(arr[:, i], window_length, poly_order) for i in range(arr.shape[1])]).T

def savitzkyGolayFilter(data, window_length, poly_order):
  return scipy.signal.savgol_filter(data, window_length, poly_order)

def applyButterLowpassFilter(arr):
  return np.array([butterLowpassFilter(arr[:, i]) for i in range(arr.shape[1])]).T

def butterLowpassFilter(data):
  nyq = 0.5 * frequency
  normal_cutoff = cutoff / nyq
  b, a = butter(order, normal_cutoff, btype='lowpass', analog=False)
  zi = lfilter_zi(b, a)
  y = lfilter(b, a, data, zi=data[0] * zi)[0]
  return y

def appendHistory(df, data_columns, label_columns, history_length):
  state_columns = [col for col in data_columns if "f" not in col]
  df_state = df[state_columns]
  df_state_history = df_state.rename(columns={col: col + "_t" for col in state_columns})
  for j in range(1, 1 + history_length):
    shifted_df = df_state.shift(j)
    for k in range(j):
      shifted_df.iloc[k] = shifted_df.iloc[j]  # repeat initial elements where shift has left NaNs
    col_names = {col: col + "_t-" + str(j) for col in list(df.columns)}
    shifted_df.rename(columns=col_names, inplace=True)
    df_state_history = pd.concat([shifted_df, df_state_history], axis=1)

  input_columns = [col for col in data_columns if "f" in col]
  df_input = df[input_columns]
  df_input_history = df_input.rename(columns={col: col + "_t" for col in input_columns})
  for j in range(1, 1 + history_length):
    shifted_df = df_input.shift(j)
    for k in range(j):
      shifted_df.iloc[k] = shifted_df.iloc[j]  # repeat initial elements where shift has left NaNs
    col_names = {col: col + "_t-" + str(j) for col in list(df.columns)}
    shifted_df.rename(columns=col_names, inplace=True)
    df_input_history = pd.concat([shifted_df, df_input_history], axis=1)

  df_history = pd.concat([df_state_history, df_input_history, df[label_columns]], axis=1)
  return df_history

def computeSpline(str, arr, t, steps, cols):
  if len(t.shape) == 1:
    t = t.reshape((t.shape[0], 1))
  splines = {}
  for i in range(len(cols)):
    splines[str + "_" + cols[i]] = scipy.interpolate.CubicSpline(t[:, 0], arr[:, i])(steps, 0)
  return splines

def nominalModel(data, thrust_coeff, torque_coeff, inertia, mass, arm_length):
  q = np.vstack((np.vstack((data["q_w"], data["q_x"])), np.vstack((data["q_y"], data["q_z"])))).T
  f = np.vstack((np.vstack((data["f_0"], data["f_1"])), np.vstack((data["f_2"], data["f_3"])))).T
  w = np.vstack((np.vstack((data["w_x"], data["w_y"])), data["w_z"])).T

  vdot = []
  for i in range(q.shape[0]):
    thrust = f[i, 0] + f[i, 1] + f[i, 2] + f[i, 3]
    quat_norm = q[i, 0] ** 2 + q[i, 1] ** 2 + q[i, 2] ** 2 + q[i, 3] ** 2
    vdot.append([
      (1. / mass) * thrust * 2. * (q[i, 0] * q[i, 2] + q[i, 1] * q[i, 3]) / quat_norm,
      (1. / mass) * thrust * 2. * (q[i, 2] * q[i, 3] - q[i, 0] * q[i, 1]) / quat_norm,
      (1. / mass) * thrust * (1. - 2. * q[i, 1] * q[i, 1] - 2. * q[i, 2] * q[i, 2]) / quat_norm - 9.8066
    ])

  wdot = []
  km_kf = torque_coeff / thrust_coeff
  for i in range(w.shape[0]):
    wdot.append([
      (arm_length * (f[i, 0] + f[i, 1] - f[i, 2] - f[i, 3])  + inertia[1] * w[i, 1] * w[i, 2] - inertia[2] * w[i, 1] * w[i, 2]) / inertia[0],
      (arm_length * (-f[i, 0] + f[i, 1] + f[i, 2] - f[i, 3]) - inertia[0] * w[i, 0] * w[i, 2] + inertia[2] * w[i, 0] * w[i, 2]) / inertia[1],
      (km_kf      * (f[i, 0] - f[i, 1] + f[i, 2] - f[i, 3])  + inertia[0] * w[i, 0] * w[i, 1] - inertia[1] * w[i, 0] * w[i, 1]) / inertia[2]
    ])

  return np.array(vdot), np.array(wdot)

# low pass filter
frequency = 100.0
cutoff = 5
order = 4
shift_step = 9

def processBag(path):
  # quadrotor physics
  mass = 0.25
  thrust_coeff = 4.37900e-09
  torque_coeff = 3.97005e-11
  arm_length = 0.076
  inertia = np.array([0.000601, 0.000589, 0.001076])

  # load dataframes
  df_odom = parseBag('/dragonfly17/odom', path)
  df_imu = parseBag('/dragonfly17/imu', path)
  df_motor = parseBag('/dragonfly17/motor_rpm', path)

  # compute time
#   t_odom = df_odom.apply(lambda r: rospy.Time(r["header.stamp.secs"], r["header.stamp.nsecs"]).to_sec(), axis=1)
#   t_imu = df_imu.apply(lambda r: (r["header.stamp.secs"] + (r["header.stamp.nsecs"] / 1e9)), axis=1)
#   t_motor = df_motor.apply(lambda r: rospy.Time(r["header.stamp.secs"], r["header.stamp.nsecs"]).to_sec(), axis=1)

  t_odom = df_odom.apply(lambda r: r["header.stamp.secs"] + r["header.stamp.nsecs"] / 1e9, axis=1)
  t_imu = df_imu.apply(lambda r: r["header.stamp.secs"] + r["header.stamp.nsecs"] / 1e9, axis=1)
  t_motor = df_motor.apply(lambda r: r["header.stamp.secs"] + r["header.stamp.nsecs"] / 1e9, axis=1)

  t_odom = t_odom.to_numpy().reshape((len(t_odom), 1))
  t_imu = t_imu.to_numpy().reshape((len(t_imu), 1))
  t_motor = t_motor.to_numpy().reshape((len(t_motor), 1))
  dt_odom = t_odom - shift(t_odom)
  dt_imu = t_imu - shift(t_imu)
  dt_motor = t_motor - shift(t_motor)
  dt_odom[np.isnan(dt_odom)] = 0.
  dt_imu[np.isnan(dt_imu)] = 0.
  dt_motor[np.isnan(dt_motor)] = 0.

  # sampling steps
  sampling_bounds = [max(np.min(t_odom), np.min(t_imu), np.min(t_motor)),
                     min(np.max(t_odom), np.max(t_imu), np.max(t_motor))]
  sampling_bounds[0] = round(sampling_bounds[0] - sampling_bounds[0] % 1. / frequency, 4)
  sampling_bounds[1] = round(sampling_bounds[1] - sampling_bounds[1] % 1. / frequency, 4)
  sampling_steps = np.arange(sampling_bounds[0], sampling_bounds[1], 1. / frequency)[:-1]

  # store all processed data in a dictionary
  sampled_data = {"t": sampling_steps}

  ## position
  p = df_odom[["pose.pose.position.x", "pose.pose.position.y", "pose.pose.position.z"]].to_numpy()
  sampled_data.update(computeSpline("p", p, t_odom, sampling_steps, "xyz"))

  ## orientation
  q = df_odom[["pose.pose.orientation.w", "pose.pose.orientation.x",
               "pose.pose.orientation.y", "pose.pose.orientation.z"]].to_numpy()
  # r = [scipy_rotation.from_quat(q[i, :]).as_matrix() for i in range(q.shape[0])]
  q = applyButterLowpassFilter(q)
  sampled_data.update(computeSpline("q", q, t_odom, sampling_steps, "wxyz"))

  ## motor speeds
  u = df_motor[["rpm_0", "rpm_1", "rpm_2", "rpm_3"]].to_numpy()
  u, t_filt, _ = dropNoise(u, t_motor, dt_motor)
  u = applyButterLowpassFilter(u)
  sampled_data.update(computeSpline("u", u, t_filt, sampling_steps, "0123"))

  ## motor thrusts
  f = (u ** 2) * thrust_coeff
  sampled_data.update(computeSpline("f", f, t_filt, sampling_steps, "0123"))

  ## linear velocity
  v = df_odom[["twist.twist.linear.x", "twist.twist.linear.y", "twist.twist.linear.z"]].to_numpy()
  v, t_filt, dt_filt = dropNoise(v, t_odom, dt_odom)
  v = applyButterLowpassFilter(v)
  # v = applySavitzkyGolayFilter(v, window_length=101, poly_order=4)
  sampled_data.update(computeSpline("v", v, t_filt, sampling_steps, "xyz"))

  ## angular velocity
  # w = df_odom[["twist.twist.angular.x", "twist.twist.angular.y", "twist.twist.angular.z"]].to_numpy()
  w = df_imu[["angular_velocity.x", "angular_velocity.y", "angular_velocity.z"]].to_numpy()
  w = w * np.array([1, -1, -1])
  w = applyButterLowpassFilter(w)
  # w = applySavitzkyGolayFilter(w, window_length=101, poly_order=4)
  sampled_data.update(computeSpline("w", w, t_imu, sampling_steps, "xyz"))

  ## linear acceleration
  vdot = differentiate(v, dt_filt)
  # vdot = differentiateFivePointStencil(v, dt_filt)
  vdot = applyButterLowpassFilter(vdot)
  # vdot = applySavitzkyGolayFilter(vdot, window_length=101, poly_order=4)
  sampled_data.update(computeSpline("vdot", vdot, t_filt, sampling_steps, "xyz"))

  ## angular acceleration
  wdot = differentiate(w, dt_imu)
  # wdot = differentiateFivePointStencil(w, dt_imu)
  wdot = applyButterLowpassFilter(wdot)
  # wdot = applySavitzkyGolayFilter(wdot, window_length=101, poly_order=4)
  sampled_data.update(computeSpline("wdot", wdot, t_imu, sampling_steps, "xyz"))

  ## nominal model
  vdot_nom, wdot_nom = nominalModel(sampled_data, thrust_coeff, torque_coeff, inertia, mass, arm_length)
  sampled_data.update(computeSpline("vdot_nom", vdot_nom, sampled_data["t"], sampling_steps, "xyz"))
  sampled_data.update(computeSpline("wdot_nom", wdot_nom, sampled_data["t"], sampling_steps, "xyz"))

  # shift filtered data
  shiftFilteredSpline(sampled_data, step=shift_step)

  # shift time so that it starts from 0.0
  sampled_data["t"] -= sampled_data["t"][0]

  return sampled_data

def extract_hdf_from_bag(bag_path,save_path):
    processed_data = processBag(bag_path)
    #remove temporary directory with generated csv files
    shutil.rmtree(Path(bag_path).with_suffix(""))

    df = pd.concat({k: pd.Series(v) for k, v in processed_data.items()}, axis=1)

    file_name = Path(bag_path).stem
    with h5py.File(Path(save_path) / (file_name + ".hdf5"), "w") as f:
        for col in df.columns:
            f.create_dataset(col, data=df[col].values, dtype='f4')

# %% ../nbs/05_quadrotor_pi.ipynb 5
def quad_pi(
        save_path: Path, #directory the files are written to, created if it does not exist
        remove_download = False
):
    save_path = Path(save_path) / 'quad_pi'


    download_dir = Path(get_tmp_benchmark_directory()) / 'Quadrotor_pi/' 
    os.makedirs(download_dir, exist_ok=True)

    url = 'https://drive.google.com/file/d/1b1PFSBlKTdrlTIurYNpTJWWEx1KIJzuR/view?usp=sharing'
    gdown.cached_download(url, str(download_dir / 'bags.zip'), postprocess=gdown.extractall,fuzzy=True)

    bag_paths = glob.glob(str(download_dir / "*.bag"))
    for bag_path in bag_paths:
        f_name = Path(bag_path).stem
        hdf_path = save_path / get_parent_dir(f_name)
        os.makedirs(hdf_path, exist_ok=True)
        
        extract_hdf_from_bag(bag_path,hdf_path)

    if remove_download:
        shutil.rmtree(download_dir)
   
