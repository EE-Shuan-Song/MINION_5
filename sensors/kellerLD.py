"""! @brief Blue Robotics Bar100 Pressure Sensor Driver.

A python module to interface with the LD line of pressure sensors from Keller.
Tested on Raspberry Pi 3 with Raspbian.

See the Keller Communication Protocol 4LD-9LD document for more details on the
I2C communication protocol, and the Keller 4LD-9LD Datasheet for sensor specification details.
"""

# Imports
import time
import smbus2 as smbus
import struct
import os
import logging

# modified by Yixuan on 10/16/2024
# added logging functions
# made minor changes in sub-functions temperature() and pressure()
# made minor changes in the main function to have better accessibility

logging.basicConfig(
    filename='log_test.log',  # Log output file
    filemode='a',  # Append to the file
    format='%(asctime)s - %(name)s - %(message)s',  # Log format (no log level)
    level=logging.INFO  # Log level
)

logger = logging.getLogger(__name__)


###### Log a message: start!
# logger.info("########################################################################")
# logger.info("kellerLD -- Blue Robotics pressure sensor called")
# logger.info("########################################################################")

class KellerLD(object):
    _SLAVE_ADDRESS = 0x40
    # I2C address of the sensor.
    _REQUEST_MEASUREMENT = 0xAC
    # Command to request a new measurement.
    _DEBUG = False
    # If enabled, extra debug messages are printed.

    def __init__(self, bus=1):
        self._bus: smbus.SMBus = None

        try:
            self._bus = smbus.SMBus(bus)
        except FileNotFoundError:
            logger.warning(f"Bus {bus} is not available. Available busses are listed as /dev/i2c*")
            if os.uname()[1] == 'raspberrypi':
                logger.warning("Enable the i2c interface using raspi-config!")

    def init(self):
        if self._bus is None:
            logger.warning("No bus!")
            return False

        # Read out minimum pressure reading
        self._bus.write_byte(self._SLAVE_ADDRESS, 0x13)
        time.sleep(0.001)
        data = self._bus.read_i2c_block_data(self._SLAVE_ADDRESS, 0, 3)

        MSWord = data[1] << 8 | data[2]
        self.debug(("0x13:", MSWord, data))

        time.sleep(0.001)
        self._bus.write_byte(self._SLAVE_ADDRESS, 0x14)
        time.sleep(0.001)
        data = self._bus.read_i2c_block_data(self._SLAVE_ADDRESS, 0, 3)

        LSWord = data[1] << 8 | data[2]
        self.debug(("0x14:", LSWord, data))

        self.pMin = MSWord << 16 | LSWord
        self.debug(("pMin", self.pMin))

        # Read out maximum pressure reading
        time.sleep(0.001)
        self._bus.write_byte(self._SLAVE_ADDRESS, 0x15)
        time.sleep(0.001)
        data = self._bus.read_i2c_block_data(self._SLAVE_ADDRESS, 0, 3)

        MSWord = data[1] << 8 | data[2]
        self.debug(("0x15:", MSWord, data))

        time.sleep(0.001)
        self._bus.write_byte(self._SLAVE_ADDRESS, 0x16)
        time.sleep(0.001)
        data = self._bus.read_i2c_block_data(self._SLAVE_ADDRESS, 0, 3)

        LSWord = data[1] << 8 | data[2]
        self.debug(("0x16:", LSWord, data))

        self.pMax = MSWord << 16 | LSWord
        self.debug(("pMax", self.pMax))

        # 'I' for 32bit unsigned int
        self.pMin = struct.unpack('f', struct.pack('I', self.pMin))[0]
        self.pMax = struct.unpack('f', struct.pack('I', self.pMax))[0]
        self.debug(("pMin:", self.pMin, "pMax:", self.pMax))

        return True

    def read(self):
        if self._bus is None:
            logger.warning("No bus!")
            return False

        if self.pMin is None or self.pMax is None:
            logger.warning("Init required!")
            logger.warning("Call init() at least one time before attempting to read()")
            return False

        self._bus.write_byte(self._SLAVE_ADDRESS, self._REQUEST_MEASUREMENT)

        time.sleep(0.01)  #10 ms, plenty of time according to spec.

        data = self._bus.read_i2c_block_data(self._SLAVE_ADDRESS, 0, 5)

        statusByte = data[0]
        pressureRaw = data[1] << 8 | data[2]
        temperatureRaw = data[3] << 8 | data[4]

        '''
        # Always busy for some reason
        busy = statusByte & 1 << 5

        if busy:
            print("Conversion is not complete.")
            return
        '''

        if statusByte & 0b11 << 3:
            logger.warning(f"Invalid mode: {((statusByte & 0b11 << 3) >> 3)}, expected 0!")
            return False

        if statusByte & 1 << 2:
            logger.warning("Memory checksum error!")
            return False

        self._pressure = (pressureRaw - 16384) * (self.pMax - self.pMin) / 32768 + self.pMin
        self._temperature = ((temperatureRaw >> 4) - 24) * 0.05 - 50

        self.debug(("data:", data))
        self.debug(("pressureRaw:", pressureRaw, "pressure:", self._pressure))
        self.debug(("temperatureRaw", temperatureRaw, "temperature:", self._temperature))

        return True

    def temperature(self):
        if self._temperature is None:
            logger.warning("Call read() first to get a measurement")
            return float('nan')
        return self._temperature

    def pressure(self):
        if self._pressure is None:
            logger.warning("Call read() first to get a measurement")
            return float('nan')
        return self._pressure

    def debug(self, msg):
        if self._DEBUG:
            print(msg)


if __name__ == '__main__':

    sensor = KellerLD()
    if not sensor.init():
        logger.error("Failed to initialize Keller LD sensor!")
        exit(1)

    while True:
        try:
            sensor.read()
            pressure = sensor.pressure()
            temperature = sensor.temperature()

            if pressure is not None and temperature is not None:
                logging.info(f"pressure: {pressure:7.4f} bar\ttemperature: {temperature:0.2f} C")
            else:
                logger.warning("Failed to retrieve valid sensor readings.")
            time.sleep(0.001)
        except Exception as e:
            logging.warning(f"Exception occurred: {e}")
