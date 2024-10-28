import os
import sys
import subprocess
import logging
import json
from typing import Optional
from sensors.ds3231 import DS3231

# re-written by Yixuan on 10/16/2024

logging.basicConfig(
    filename='log_test.log',  # Log output file
    filemode='a',  # Append to the file
    format='%(asctime)s - %(name)s - %(message)s',  # Log format (no log level)
    level=logging.INFO  # Log level
)
logger = logging.getLogger(__name__)


class MinionToolbox:
    # define True or False
    ON = True
    OFF = False

    def __init__(self):
        self._py_ver_major = sys.version_info.major
        self._rtc_ext = DS3231()

    @staticmethod
    def check_wifi(skip_minion_hub=False):
        """
        Checks for a Master_Hub or Minion_Hub and connects.

        Parameters:
        ----------
        bool skip_minion_hub : Connect to Minion Hub if found (False), skip if True.

        Returns:
        --------
        string status : "Connected" or "Not Connected"

        Examples:
        check_wifi()  # Connects to any available hub
        check_wifi(skip_minion_hub=True)  # Skips Minion_Hub if found
        """

        # Initialize status
        status = "Not Connected"

        try:
            # Run the `iwlist` command to scan available networks
            result = subprocess.run(['/usr/sbin/iwlist', 'wlan0', 'scan'], capture_output=True, text=True, check=True)
            out = result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to scan Wi-Fi networks: {e}")
            return "Not Connected"

        # Check for available SSIDs in priority order
        for ssid in ('Master_Hub', 'Minion_Hub'):
            if ssid in out:
                if ssid == 'Minion_Hub' and skip_minion_hub:
                    logger.info("[ Skipping Minion Hub. ]")
                    # Skip connecting to Minion_Hub if IgnoreStatus is True
                    continue

                # Print which hub we're connecting to
                logger.info(f"[ Connecting to {ssid} ]")
                status = "Connected"
                break

        if status == "Not Connected":
            logger.info("[ No WIFI found. ]")

        return status

    @staticmethod
    def ans2bool(ans2convert) -> bool:
        """Convert a yes/no or true/false answer to a boolean.

        Answers that result in True:
            "Y", "y", "yes", "true", "t", "1", "on", "enabled", "ok"
        Answers that result in False:
            "N", "n", "no", "false", "f", "0", "off", "disabled"

        Parameters:
        ----------
        ans2convert : str or None
            Answer to convert.

        Returns:
        -------
        bool
            Boolean representation of the answer.

        Example:
            result = ans2bool("Y")
            print(result)  # True
        """
        if not ans2convert:  # Handle None or empty input
            return False

        true_values = {"y", "yes", "true", "t", "1", "on", "enabled"}
        false_values = {"n", "no", "false", "f", "0", "off", "disabled"}

        ans_lower = ans2convert.strip().lower()

        if ans_lower in true_values:
            return True
        elif ans_lower in false_values:
            return False
        else:
            logging.error(f"Invalid input: {ans2convert!r}. Cannot convert to boolean.")
            raise ValueError(f"Invalid input: {ans2convert!r}. Cannot convert to boolean.")

    def rtc_time(self) -> str:
        """Read the Date and Time from the DS3231 External RTC.

        Parameters:
        ----------
        None

        Returns:
        -------
        str
        time_stamp : Formatted Date and Time string (YYYY-MM-DD_hh-mm-ss)
        """
        time_stamp = "9999-99-99_99-99-99"  # Default in case of failure
        try:
            # Get the Date and Time from the DS3231 RTC
            tm_now_dict = self._rtc_ext.read_time()

            # Create the time stamp using f-strings
            time_stamp = (
                f"{tm_now_dict['YYYY']}-{tm_now_dict['MM']}-{tm_now_dict['DD']}_"
                f"{tm_now_dict['hh']}-{tm_now_dict['mm']}-{tm_now_dict['ss']}"
            )

        except PermissionError:
            logger.error("Permission denied. Superuser access might be required.")
            print("Hint: Super User Permission Required for accessing the time stamp pickle.")
        except Exception as e:
            logger.error(f"Unexpected error occurred while reading RTC: {str(e)}")

        return time_stamp

    @staticmethod
    def sync_rpi_time():
        """
        Synchronizes the Raspberry Pi system time with the RTC (DS3231) using hwclock.

        Raises:
        -------
        - PermissionError: If the synchronization requires superuser privileges.
        - RuntimeError: If hwclock command fails.
        """
        try:
            # Run the hwclock command to sync the system time with the RTC
            result = subprocess.run(
                ["sudo", "hwclock", "-s"], capture_output=True, text=True, check=True
            )
            logger.info("System time synchronized with RTC using hwclock.")
            print("System time synchronized with RTC.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to synchronize system time: {e.stderr}")
            raise RuntimeError(f"Failed to synchronize system time: {e.stderr}") from e
        except PermissionError:
            logger.error("Superuser privileges are required to run hwclock.")
            raise PermissionError("Superuser privileges are required to run hwclock.")

    # need updates/changes below
    @staticmethod
    def sleep_rpi(seconds=600):  # need to test
        os.system(f"sudo rtcwake -m mem -s {seconds}")

    def create_json(self, file_path: str, total_samples: int, end_time: Optional[str] = None):
        """
        Creates a JSON file with the specified path and filename.
        Records the start time, total samples, remaining samples, and end time.

        Parameters:
        ----------
        - file_path (str): The path and name of the JSON file.
        - total_samples (int): The total number of samples.
        - end_time (Optional[str]): The specified end time.
        """
        # Extract the directory path from the file path
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        # Set the start time using the RTC time
        start_time = self.rtc_time()

        if end_time is None:
            end_time = "2099-12-31_23-59-59"
            logger.info(f"End time not specified. Using default: {end_time}")

        # Prepare the JSON data
        data = {
            "start_time": start_time,
            "total_samples": total_samples,
            "remaining_samples": total_samples,  # Initially same as total samples
            "end_time": end_time
        }

        try:
            # Write the data to the JSON file
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)  # Pretty-print with indent

            print(f"JSON file created at: {file_path} with initial data:")
            logger.info(f"JSON file created at: {file_path}")
        except Exception as e:
            logger.error(f"Failed to write JSON file '{file_path}': {str(e)}")
            raise

    @staticmethod
    def read_json(file_path: str):
        """
        Reads a JSON file and returns the start time, total samples,
        remaining samples, and end time.

        Parameters:
        ----------
        - file_path (str): The path to the JSON file to be read.

        Returns:
        --------
        - tuple: A tuple containing (start_time, total_samples, remaining_samples, end_time).

        Raises:
        -------
        - FileNotFoundError: If the specified file does not exist.
        - KeyError: If the expected keys are missing from the JSON file.
        """
        # Check if the JSON file exists
        if not os.path.exists(file_path):
            logger.error(f"File '{file_path}' not found.")
            raise FileNotFoundError(f"File '{file_path}' not found.")

        # Read the JSON file
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Extract the required fields
            start_time = data["start_time"]
            total_samples = data["total_samples"]
            remaining_samples = data["remaining_samples"]
            end_time = data["end_time"]

            return start_time, total_samples, remaining_samples, end_time

        except KeyError as e:
            logger.error(f"Missing key {str(e)} in JSON file '{file_path}'.")
            raise KeyError(f"Missing key {str(e)} in JSON file '{file_path}'.")

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from file '{file_path}': {str(e)}")
            raise ValueError(f"Error decoding JSON from file '{file_path}': {str(e)}")

    @staticmethod
    def update_json(file_path: str, remaining_samples: int, end_time: Optional[str] = None):
        """
        Updates the JSON file with new values for remaining samples and optionally the end time.

        Parameters:
        ----------
        - file_path (str): The path to the JSON file to be updated.
        - remaining_samples (int): The new value for remaining samples.
        - end_time (Optional[str]): The new end time in 'YYYY-MM-DD_hh-mm-ss' format (optional).

        Raises:
        --------
        - FileNotFoundError: If the specified JSON file does not exist.
        - ValueError: If the remaining_samples is not an integer.
        """
        # Check if the JSON file exists
        if not os.path.exists(file_path):
            logger.error(f"File '{file_path}' not found.")
            raise FileNotFoundError(f"File '{file_path}' not found.")

        try:
            # Read the current data from the JSON file
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Update the remaining samples
            data["remaining_samples"] = remaining_samples
            logger.info(f"Updated 'remaining_samples' to {remaining_samples} in '{file_path}'.")

            # Optionally update the end time
            if end_time:
                data["end_time"] = end_time
                logger.info(f"Updated 'end_time' to {end_time} in '{file_path}'.")

            # Write the updated data back to the JSON file
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)

            print(f"Successfully updated '{file_path}'.")
            logger.info(f"Successfully updated '{file_path}'.")

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from '{file_path}': {str(e)}")
            raise ValueError(f"Error decoding JSON from '{file_path}': {str(e)}")

        except KeyError as e:
            logger.error(f"Missing key {str(e)} in JSON file '{file_path}'.")
            raise KeyError(f"Missing key {str(e)} in JSON file '{file_path}'.")
