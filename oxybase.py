import logging
import os
import time
import serial
import minion_hat_gpio

# written by Yixuan on 10/22/2024
#
# example:
# oxy_sensor = Oxybase(filename='Minion_Oxy/Oxy_log.csv')
# with open(oxy_sensor._filename, 'a') as f:
#     for i in range(1000):
#         real_time, data = oxy_sensor.sample()
#         f.write(f"{real_time},{data}\n")
#         time.sleep(1.0)
# oxy_sensor.shutdown()
# oxy_sensor.close()


# Configure logging
logging.basicConfig(
    filename='log_test.log',
    filemode='a',
    format='%(asctime)s - %(name)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class Oxybase:
    def __init__(self, filename=None, port='/dev/serial0', baudrate=19200):
        """Initialize the Oxybase sensor, serial connection, and log file."""
        self._filename = self.setup_file(filename)

        # Setup serial connection
        try:
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1
            )
            logger.info(f"Serial port {port} configured successfully.")
        except serial.SerialException as e:
            logger.error(f"Failed to configure serial port: {e}")

        try:
            minion_hat_gpio.oxybase_enable(True)
            time.sleep(4)  # 4-second warmup
            self.ser.flushInput()  # clear the input buffer
            self.ser.flushOutput()  # clear the output buffer
            self.ser.write(b'mode0001\r')  # send initialization command
            time.sleep(1)
            logger.info("Oxybase sensor powered ON and initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Oxybase sensor: {e}")

    @staticmethod
    def setup_file(path):
        """Ensure the log file and directory exist."""
        if not path:
            path = 'Minion_O2/O2_log.csv'

        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        if not os.path.isfile(path):
            with open(path, 'w') as f:
                f.write("timestamp,data\n")
            logger.info(f"Log file created at: {path}")
        else:
            logger.info(f"Using existing log file: {path}")

        return path

    def sample(self):
        """Take a sample from the Oxybase sensor and log the data."""
        try:
            self.ser.flushInput()
            self.ser.flushOutput()
            self.ser.write(b'data\r')  # request data from the sensor
            reply = self.ser.read_until(b'\r')  # read data
            data = reply.decode('utf-8').strip()  # decode the data

            timestamp = time.time()
            current_time = f"{time.strftime('%Y%m%d_%H%M%S', time.gmtime(timestamp))}"
            logger.debug(f"O2 sampled at {current_time}")

            return current_time, data

        except Exception as e:
            logger.error(f"Error reading Oxybase sensor: {e}")
            return None, None

    def shutdown(self):
        """Shut down the Oxybase sensor."""
        try:
            self.ser.write(b'mode0000\r')  # send shutdown command
            minion_hat_gpio.oxybase_enable(False)  # disable the power
            logger.info("Oxybase sensor powered OFF.")
        except Exception as e:
            logger.error(f"Error during sensor shutdown: {e}")

    def close(self):
        """Close the serial connection."""
        self.ser.close()
        logger.info("Serial connection closed.")
