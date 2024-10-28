import logging
import os
import time
from sensors.tsys01 import TSYS01  # temperature sensor
from sensors.ms5837 import MS5837  # iniP30
from sensors.kellerLD import KellerLD  # iniP100

# written by Yixuan on 10/22/2024
# partially referred to Nils' tp.py
# now including two different options of pressure sensors
#
# example:
# tp = TP(
#     filename='Minion_data/TP_log.csv',
#     use_temp=True,
#     use_iniP30=True,
#     use_iniP100=False
# )
# with open(tp._filename, 'a') as f:
#     for i in range(1000):
#         # Take a sample from the sensors
#         real_time, temperature, pressure, aux_temperature = tp.sample()
#         f.write(f"{real_time},{temperature:.4f},{pressure:.3f},{aux_temperature:.2f}\n")
#         time.sleep(1.0)


logging.basicConfig(
    filename='log_test.log',  # Log output file
    filemode='a',  # Append to the file
    format='%(asctime)s - %(name)s - %(message)s',  # Log format (no log level)
    level=logging.INFO  # Log level
)

logger = logging.getLogger(__name__)

depth_factor = .01
surface_offset = 10


class TP:
    def __init__(self, filename=None, use_temp=True, use_iniP30=False, use_iniP100=True):

        # initialize the sensors
        if use_temp:
            try:
                self.Temp_sensor = TSYS01()
                self.Temp_sensor.init()
                logger.info("Temperature sensor initialized successfully.")
            except OSError:
                logger.warning('Error initializing temperature sensor.')

        if use_iniP30:
            try:
                self.Pressure_sensor = MS5837()
                self.Pressure_sensor.init()
                logger.info("iniP30 pressure sensor initialized successfully.")
            except OSError:
                logger.warning('Error initializing pressure iniP30 sensor.')
        elif use_iniP100:
            try:
                self.Pressure_sensor = KellerLD()
                self.Pressure_sensor.init()
                logger.info("iniP100 pressure sensor initialized successfully.")
            except OSError:
                logger.warning('Error initializing pressure iniP100 sensor.')

        self._filename = self.setup_file(filename)

    @staticmethod
    def setup_file(path):
        """Set up the log file and ensure the directory exists."""
        if path is None:
            path = 'Minion_TP/TP_log.csv'

        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        if not os.path.isfile(path):
            with open(path, 'w') as f:
                f.write("timestamp,temperature,pressure,aux_temperature\n")
            logger.info(f"TP Log file created at: {path}")
        else:
            logger.info(f"Using existing TP log file: {path}")

        return path

    def sample(self):
        # Read sensors
        t, p, pt = float('nan'), float('nan'), float('nan')
        try:
            t = self.Temp_sensor.read()
        except OSError:
            logger.warning('Error reading temperature sensor.')
        try:
            p, pt = self.Pressure_sensor.read()
            p = round(p * depth_factor - surface_offset, 3)
        except OSError:
            logger.warning('Error reading pressure sensor.')

        timestamp = time.time()
        current_time = f"{time.strftime('%Y%m%d_%H%M%S', time.gmtime(timestamp))}"
        logger.debug(f"TP sampled at {current_time}")
        logger.info(f'Logged TP: {t:.4f},{p:.3f},{pt:.2f}')
        return current_time, t, p, pt
