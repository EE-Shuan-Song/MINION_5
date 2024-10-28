#!/usr/bin/env python3

import time
import os
import sys
import logging
import configparser
from dataclasses import dataclass
from minion_tools import MinionToolbox
from minion_hat_i2c import MinionHat
from minion_camera import Camera
from tp import TP
import minion_hat_gpio

# re-written by Yixuan on 10/16/2024
# the older version used to be "Minion_DeploymentHandler.py"
# now we are reading the minion configuration file in this main function
# added logging functions


# ----------------------------------------------------------------------------------------------------------------------
# Initialize the logging function
# ----------------------------------------------------------------------------------------------------------------------

logging.basicConfig(
    filename='log_test.log',  # Log output file
    filemode='a',  # Append to the file
    format='%(asctime)s - %(name)s - %(message)s',  # Log format (no log level)
    level=logging.INFO  # Log level
)

logger = logging.getLogger(__name__)
logger.info("########################################################################")
logger.info("Minion Deployment Handler called")
logger.info("########################################################################")
print("Minion Deployment Handler called")

# ----------------------------------------------------------------------------------------------------------------------
# create instances of MinionToolbox and MinionHat
# and other preparations
# ----------------------------------------------------------------------------------------------------------------------

minion_hat_gpio.init()  # initialize the gpio first. otherwise we will see undefined pin in log files
minion_tools = MinionToolbox()
minion_hat = MinionHat()
minion_tools.sync_rpi_time()  # always synchronize the rpi time with rtc

# ----------------------------------------------------------------------------------------------------------------------
# load the data configuration file
# ----------------------------------------------------------------------------------------------------------------------
minion_config_file = 'Minion_config.ini'


@dataclass
class MissionConfig:
    Minion_ID: str
    Abort: bool
    MAX_Depth: float
    IG_WIFI_H: float

    INIsamp_hours: float
    INIsamp_camera_period: float
    INIsamp_tempPres_period: float
    INIsamp_oxygen_period: float

    FINsamp_hours: float
    FINsamp_camera_period: float
    FINsamp_tempPres_period: float
    FINsamp_oxygen_period: float

    TLPsamp_hours: float
    TLPsamp_burst_minutes: float
    TLPsamp_camera_period: float
    TLPsamp_tempPres_period: float
    TLPsamp_oxygen_period: float
    TLPsamp_interval_minutes: float

    gps_transmission_window: float
    gps_transmission_interval: float

    iniImg: bool
    iniP30: bool
    iniP100: bool
    iniTmp: bool
    iniO2: bool


config = configparser.ConfigParser()
config.read(minion_config_file)

try:
    mission = MissionConfig(
        Minion_ID=str(config['MINION']['number']),
        Abort=MinionToolbox.ans2bool(config['Mission']['abort']),
        MAX_Depth=float(config['Mission']['max_depth']),
        IG_WIFI_H=float(config['Mission']['ignore_wifi-hours']),

        INIsamp_hours=float(config['Initial_Samples']['hours']),
        INIsamp_camera_period=float(config['Initial_Samples']['camera_sample_period']),
        INIsamp_tempPres_period=float(config['Initial_Samples']['temppres_sample_period']),
        INIsamp_oxygen_period=float(config['Initial_Samples']['oxygen_sample_period']),

        FINsamp_hours=float(config['Final_Samples']['hours']),
        FINsamp_camera_period=float(config['Final_Samples']['camera_sample_period']),
        FINsamp_tempPres_period=float(config['Final_Samples']['temppres_sample_period']),
        FINsamp_oxygen_period=float(config['Final_Samples']['oxygen_sample_period']),

        TLPsamp_hours=float(config['Time_Lapse_Samples']['hours']),
        TLPsamp_burst_minutes=float(config['Time_Lapse_Samples']['sample_burst_duration']),
        TLPsamp_camera_period=float(config['Time_Lapse_Samples']['camera_sample_period']),
        TLPsamp_tempPres_period=float(config['Time_Lapse_Samples']['temppres_sample_period']),
        TLPsamp_oxygen_period=float(config['Time_Lapse_Samples']['oxygen_sample_period']),
        TLPsamp_interval_minutes=float(config['Time_Lapse_Samples']['sample_interval_minutes']),

        gps_transmission_window=float(config['GPS']['gps_transmission_window']),
        gps_transmission_interval=float(config['GPS']['gps_transmission_interval']),

        iniImg=MinionToolbox.ans2bool(config['Sampling_scripts']['image']),
        iniP30=MinionToolbox.ans2bool(config['Sampling_scripts']['30ba-pres']),
        iniP100=MinionToolbox.ans2bool(config['Sampling_scripts']['100ba-pres']),
        iniTmp=MinionToolbox.ans2bool(config['Sampling_scripts']['temperature']),
        iniO2=MinionToolbox.ans2bool(config['Sampling_scripts']['oxybase']),
    )
    logger.info("Minion configuration file loaded!")
    print("Minion configuration file loaded!")

except KeyError as e:
    logger.error(f"Error: Missing configuration key - {e}")
    print(f"Error: Missing configuration key - {e}")
except ValueError as e:
    logger.error(f"Error: Invalid configuration key - {e}")
    print(f"Error: Invalid value in configuration - {e}")


# ----------------------------------------------------------------------------------------------------------------------
# run the main function
# ----------------------------------------------------------------------------------------------------------------------

# first step: check if wifi is connected
if minion_tools.check_wifi() == "Connected":
    # print on the test monitor but also log the situation
    print("Minion started but Wifi connected. Standby")
    logger.warning("Minion started but Wifi connected. Standby")
    # flash the LED ring twice, each loop has 250 ms on, 250 ms off
    minion_hat_gpio.light_ring_set(True)
    # minion_hat_gpio.light_ring_flash_set(2, 250, 250)
    # keep the green LED on
    minion_hat_gpio.led_green(True)
    time.sleep(2)
    minion_hat_gpio.led_green(False)
    time.sleep(2)
    minion_hat_gpio.led_red(True)
    time.sleep(2)
    minion_hat_gpio.led_red(False)
    time.sleep(2)
    minion_hat_gpio.led_blue(True)
    time.sleep(2)
    minion_hat_gpio.led_blue(False)
    # terminate the program
    time.sleep(10)
    exit(0)
else:
    camera_ini = Camera("/home/minion/test_imgs", capture_camera_settings=True)
    camera_ini.set_config('auto')
    camera_ini.picture()

