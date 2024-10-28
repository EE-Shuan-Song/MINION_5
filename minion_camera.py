#!/usr/bin/env python
from picamera2 import Picamera2
import os
import json
import logging
import time
import minion_hat_gpio

# written by Yixuan on 10/18/2024
# partially referred to Nils' camera.py or dual_camera.py
# now saving time from RTC but recording the machine time in the log file
# removed the prefix
#
#
# we will need to modify the path to save pics in INI, FIN, or TLP. for example
# camera_ini = Camera("/home/pi/media/INI", capture_camera_settings=True)
# camera_ini.picture()  # Capture pictures in INI folder
#
# camera_fin = Camera("/home/pi/media/FIN", capture_camera_settings=True)
# camera_fin.video(duration=15)  # Record videos in FIN folder


logging.basicConfig(
    filename='log_test.log',  # Log output file
    filemode='a',  # Append to the file
    format='%(asctime)s - %(name)s - %(message)s',  # Log format (no log level)
    level=logging.INFO  # Log level
)

logger = logging.getLogger(__name__)
###### Log a message: start!
# logger.info("########################################################################")
# logger.info("Minion Camera called")
# logger.info("########################################################################")


class Camera:
    # initialize the camera within the class
    def __init__(self, path, capture_camera_settings=True):
        # initialize the led ring
        minion_hat_gpio.init()
        self.cam = Picamera2()
        self.path = path
        self.capture_camera_settings = capture_camera_settings
        self.config = {
            'auto': {},  # Auto
            'pic01': {"ExposureTime": 50000, "AnalogueGain": 3.0, "ColourGains": (4.0, 1.0)},  # Summer 2023 Settings
        }
        for config in self.config.keys():
            os.makedirs(os.path.join(path, config), exist_ok=True)

    def __del__(self):
        self.cam.close()

    def set_config(self, mode):
        """Set the active configuration mode."""
        # Handle 'auto' or {'auto'} inputs
        if isinstance(mode, str) and mode in self.config:
            self.config = {mode: self.config[mode]}
        else:
            logger.error(f"Invalid configuration mode: {mode}")
            raise ValueError(f"Invalid configuration mode: {mode}")

    def picture(self):
        """
        Parameters:
        ----------
        None

        Returns:
        -------
        pictures saved

        """
        minion_hat_gpio.light_ring_set(True)
        for mode, config in self.config.items():
            # configurate the camera settings
            self.cam.configure(self.cam.create_still_configuration())
            if config:
                self.cam.set_controls(config)
            self.cam.start()
            time.sleep(1.0)  # wait for initialization

            # Generate timestamp-based filename
            timestamp = time.time()
            # I like the ms setting since the interval may vary
            ms = f'{timestamp:.3f}'[-3:]
            current_time = f"{time.strftime('%Y%m%d_%H%M%S', time.gmtime(timestamp))}.{ms}"
            logger.info(f"Capture pic [{mode}] .jpg at {current_time}")

            self.cam.capture_file(os.path.join(self.path, mode, current_time + '.jpg'))

            # Save metadata if capture settings are enabled
            if self.capture_camera_settings:
                with open(os.path.join(self.path, mode, current_time + '.json'), 'w') as f:
                    f.write(json.dumps(self.cam.capture_metadata()))
            self.cam.stop()
        minion_hat_gpio.light_ring_set(False)

    def video(self, duration=10):
        """Record videos for each configuration mode.

        Parameters
        ----------
        duration : int, optional
            Duration of the video in seconds (default is 10 seconds).
        """
        minion_hat_gpio.light_ring_set(True)  # Turn on the light ring
        try:  # want to be more cautious when taking videos
            self.cam.start()

            for mode, config in self.config.items():
                try:
                    # Configure the camera settings for video
                    self.cam.configure(self.cam.create_video_configuration())
                    if config:
                        self.cam.set_controls(config)
                    time.sleep(1.0)  # wait for initialization

                    # Generate timestamp-based filename
                    timestamp = time.time()
                    current_time = f"{time.strftime('%Y%m%d_%H%M%S', time.gmtime(timestamp))}"

                    # Log the start of the video capture
                    logger.info(f"Start recording video [{mode}] at {current_time}")

                    # Start recording the video
                    video_filename = os.path.join(self.path, mode, f"{current_time}.h264")
                    self.cam.start_recording(video_filename)
                    time.sleep(duration)
                    self.cam.stop_recording()
                    logger.debug(f"Video recording [{mode}] completed.")

                    # Save metadata if capture settings are enabled
                    if self.capture_camera_settings:
                        metadata_path = os.path.join(self.path, mode, f"{current_time}.json")
                        with open(metadata_path, 'w') as f:
                            f.write(json.dumps(self.cam.capture_metadata()))

                except Exception as e:
                    # Log any errors that occur during video capture
                    logger.error(f"Error recording video: {str(e)}")

        finally:
            self.cam.stop()
            minion_hat_gpio.light_ring_set(False)  # Turn off the light ring
