import logging
import time
from minion_hat_i2c import MinionHat
from sensors.minsat import MinSat

# Written by Yixuan on 10/23/2024
# This class combines the functionality of xmt_minion_data.py and Recovery_Sampler_Burn.py
# It activates the burn wire and manages GPS data transmission and file transfer via satellite modem.
#
#
# Example:
# from recovery import Recovery
# recovery = Recovery()
# total_duration = 24 * 60 * 60  # 6 hours
# interval = 10 * 60  # 10 minutes
# start_time = time.time()  # Record the start time
# while time.time() - start_time < total_duration:
#     recovery.acquire_and_send_gps_position()
#     time.sleep(interval)
#
# recovery.transmit_file(filename, start_file_position):
# recovery.cleanup()

logging.basicConfig(
    filename='log_test.log',  # Log output file
    filemode='a',  # Append to the file
    format='%(asctime)s - %(name)s - %(message)s',  # Log format
    level=logging.INFO  # Log level
)
logger = logging.getLogger(__name__)


class Recovery:
    def __init__(self, gps_port="/dev/ttySC0", gps_baud=9600, modem_port="/dev/ttySC1", modem_baud=19200):
        """
        Initialize the Recovery class with GPS and modem settings, and create instances of MinionHat and MinSat.
        """
        self.gps_port = gps_port
        self.gps_baud = gps_baud
        self.modem_port = modem_port
        self.modem_baud = modem_baud

        # Initialize MinionHat and MinSat instances
        self.minion_hat = MinionHat()
        self.m1 = MinSat(self.gps_port, self.gps_baud, self.modem_port, self.modem_baud)

        # Strobe settings
        self._STROBE_ON = 100  # Strobe on time in milliseconds
        self._STROBE_OFF = 4900  # Strobe off time in milliseconds

    def acquire_and_send_gps_position(self):
        """
        Acquires a GPS position and sends it via the satellite modem.
        Manages retries and logs the status.
        """
        # Activate the burn wire and strobe
        # I added the burn wire here because the burn wire is always called with sbd_send_position
        logger.info("Activating burn wire and strobe.")
        print("Activating burn wire and strobe.")
        self.minion_hat.burn_wire(self.minion_hat.ENABLE)
        self.minion_hat.strobe_timing(self._STROBE_ON, self._STROBE_OFF)
        self.minion_hat.strobe(self.minion_hat.ENABLE)

        # Attempt to acquire and send GPS position
        logger.info("Attempting to acquire and send GPS position.")
        print("Attempting to acquire and send GPS position.")
        success, ret_data = self.m1.sbd_send_position(verbose=False, maintain_gps_pwr=True, gps_timeout=120)

        if success and ret_data.valid_position:
            logger.info("[OK] GPS Position Acquired and Transmitted to Iridium Successfully.")
            print("[OK] GPS Position Acquired and Transmitted to Iridium Successfully.")
        else:
            logger.warning("[FAILURE] GPS transmission failed. Retrying...")
            print("[FAILURE] GPS transmission failed. Retrying...")

            # Retry GPS transmission
            success, ret_data = self.m1.sbd_send_position(verbose=False, maintain_gps_pwr=False, gps_timeout=120)
            if success and ret_data.valid_position:
                logger.info("[OK] GPS Position Acquired and Transmitted Successfully on Retry.")
                print("[OK] GPS Position Acquired and Transmitted Successfully on Retry.")
            else:
                logger.error("[FAILURE] GPS transmission failed after retry.")
                print("[FAILURE] GPS transmission failed after retry.")

        # Turn off GPS and modem power after transmission
        self.m1.gps_pwr(self.m1.dev_off)
        self.m1.modem_pwr(self.m1.dev_off)

    def transmit_file(self, filename, start_file_position):
        """
        Transmit a file using the satellite modem with a maximum of 5 attempts.
        If transmission fails 5 times, it reports failure due to the nature of uncertainty in the sensor.
        """
        attempt = 0
        max_tries = 5

        while attempt < max_tries:
            attempt += 1
            logger.info(f"Attempt {attempt} - Transmitting file: {filename}")
            print(f"Attempt {attempt} - Transmitting file: {filename}")

            # Transmit the file
            ret_data = self.m1.sbd_send_file(
                filename=filename,
                verbose=False,
                num_header_lines=0,
                start_file_position=start_file_position
            )

            # Check the result
            if ret_data:
                logger.info("[OK] File transmitted successfully.")
                print("[OK] File transmitted successfully.")
                return  # Exit the function on success

            # Log the failure and try again
            logger.warning(f"[FAILURE] Attempt {attempt} failed to transmit the file.")
            print(f"[FAILURE] Attempt {attempt} failed to transmit the file.")

        # If all attempts fail
        logger.error(f"[FAILURE] File transmission failed after {max_tries} attempts.")
        print(f"[FAILURE] File transmission failed after {max_tries} attempts.")
        print("[INFO] Failure due to the nature of uncertainty in the sensor.")

    def cleanup(self):
        """
        Clean up resources by turning off the modem and deleting the instance.
        """
        logger.info("Cleaning up modem resources.")
        self.m1.modem_pwr(self.m1.dev_off)
        del self.m1

