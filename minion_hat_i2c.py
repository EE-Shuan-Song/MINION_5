# Imports
import smbus2 as smbus
import time
import os
import logging

# modified by Yixuan on 10/10/2024
# added logging functions
# replaced smbus by smbus2 following Nils
# Minion_Hat is actually a wrapper for I2C communication

logging.basicConfig(
    filename='log_test.log',  # Log output file
    filemode='a',  # Append to the file
    format='%(asctime)s - %(name)s - %(message)s',  # Log format (no log level)
    level=logging.INFO  # Log level
)

logger = logging.getLogger(__name__)
###### Log a message: start!
# logger.info("########################################################################")
# logger.info("Minion Hat called")
# logger.info("########################################################################")

class MinionHat(object):

    # Device I2C Address
    _DEV_ADDR = 0x30

    # Minion Hat Register Definitions
    _LED = 0x01         # Status LED Register
    _SHDN = 0x02        # Shutdown Command Register
    _SLP = 0x03         # Sleep Command Register
    _SHDNDLY = 0x04     # Delay time before shutting down RPI
    _SLPB0 = 0x05       # Sleep Time Low Byte 0 Register
    _SLPB1 = 0x06       # Sleep Time Low Byte 1 Register
    _SLPB2 = 0x07       # Sleep Time Low Byte 2 Register
    _SLPB3 = 0x08       # Sleep Time Low Byte 3 Register
    _STRBONH = 0x09     # Most Significant Byte of the 16-bit Strobe On Register
    _STRBONL = 0x0A     # Least Significant Byte of the 16-bit Strobe On Register
    _STRBOFFH = 0x0B    # Most Significant Byte of the 16-bit Strobe Off Register
    _STRBOFFL = 0x0C    # Least Significant Byte of the 16-bit Strobe Off Register
    _STRBEN = 0x0D      # Recovery Strobe On/Off Register
    _BRNWIRE = 0x0E     # Burn Wire activation Register
    _BRPWR = 0x0F       # Blue Robotics Connectors Power Control Register
    _PUEN = 0x10        # External Pull-Up Resistor Enable, 0:Disable 1:Enable

    # Definitions
    ENABLE = [0x01]
    DISABLE = [0x00]
    ON = [0x01]
    OFF = [0x00]

    def __init__(self, _bus=1):
        self._bus = None

        try:
            self._bus = smbus.SMBus(_bus)
        except FileNotFoundError:
            logger.warning(f"Bus {_bus} is not available. Available busses are listed as /dev/i2c*")
            if os.uname()[1] == 'raspberrypi':
                logger.warning("Enable the i2c interface using raspi-config!")

    def _write_block_data(self, device_addr, device_reg, data):
        """Write I2C Block Data to an external device

        Parameters
        ----------
        device_addr : I2C device address
        device_reg  : I2C device register address
        data        : Data to transmit

        Returns:
        --------
        success     : True (Data written successfully) or False

        """

        try_counter = 10  # Try at most 10 time to write the data
        success = False

        while try_counter:
            try_counter -= 1
            try:
                self._bus.write_i2c_block_data(device_addr, device_reg, data)
                success = True
                break
            except:
                logger.warning(f'[ Error ] I2C Bus Error try #{try_counter}')
                pass

        time.sleep(.1)  # Delay for PIC16LF1847 to process command
        return success

    def led(self, new_state):
        """Status LED Control
        Blue LED requires the I2C signal transmitting

        Parameters:
        ----------
        new_state : ON or OFF

        Returns:
        --------
        none

        Example:
        --------
        from minion_hat import MinionHat
        min_hat = MinionHat()
        min_hat.led(min_hat.ON)  # Turn on the LED
        min_hat.led(min_hat.OFF)  # Turn off the LED

        """
        # self._bus.write_i2c_block_data(self._DEV_ADDR, self._LED, new_state)
        status = self._write_block_data(self._DEV_ADDR, self._LED, new_state)
        # time.sleep(.1)

    def shutdown(self, shutdown_secs):
        """Shutdown the RPi and Put the Minion Hat into Low Power Mode for shutdown_secs.
            Warning!: cancels the burn wire and recovery strobe.

        Parameters
        ----------
        shutdown_secs : shutdown time in seconds   (range: 0-2^32)

        Returns:
        --------
        none

        Example:
        --------
        from minion_hat import MinionHat
        min_hat = MinionHat()
        min_hat.shutdown(120)

        """

        # Configure the sleep time
        self.sleep_time(shutdown_secs)

        # Transmit the Shutdown Command
        # self._bus.write_i2c_block_data(self._DEV_ADDR, self._SHDN, self.ENABLE)
        status = self._write_block_data(self._DEV_ADDR, self._SHDN, self.ENABLE)
        logger.debug("Entering Lowest Power Shutdown Mode...")
        time.sleep(1)
        os.system("sudo shutdown now")

    def sleep(self, sleep_secs):
        """Shutdown the RPi.  Minion Hat functions still operating.

        Parameters
        ----------
        sleep_secs : sleep time in seconds   (range: 0-2^32)

        Returns:
        --------
        none

        Example:
        --------
        from minion_hat import MinionHat
        min_hat = MinionHat()
        min_hat.sleep(120)

        """

        # Configure the sleep time
        self.sleep_time(sleep_secs)

        # Transmit the Sleep Command
        # self._bus.write_i2c_block_data(self._DEV_ADDR, self._SLP, self.ENABLE)
        status = self._write_block_data(self._DEV_ADDR, self._SLP, self.ENABLE)
        logger.debug("Entering Low Power Sleep Mode...")
        time.sleep(1)
        os.system("sudo shutdown now")

    def shutdown_delay(self, delay_secs):
        """Configure the delay before powering down the RPi during sleep or shutdown operations.

        Parameters
        ----------
        delay_secs : delay time in seconds   (range: 0-255)

        Returns:
        --------
        none

        Example:
        --------
        from minion_hat import MinionHat
        min_hat = MinionHat()
        min_hat.shutdown_delay(10) # Configure to delay 10 seconds before powering down the RPi

        """

        # self._bus.write_i2c_block_data(self._DEV_ADDR, self._SHDNDLY, [delay_secs])
        status = self._write_block_data(self._DEV_ADDR, self._SHDNDLY, [delay_secs])  # TODO: Implement Status usage
        # time.sleep(.1)

    def sleep_time(self, sleep_secs):
        """Configure the sleep time.

        Parameters
        ----------
        sleep_secs : sleep time in seconds   (range: 1-2^32)

        Returns:
        --------
        error_flag : False, No errors   True, error detected

        Example:
        --------
        from minion_hat import MinionHat
        min_hat = MinionHat()
        min_hat.sleep_time(120) # Configure 2-min sleep time

        """

        error_flag = False

        # Range Check
        if sleep_secs < 1 or sleep_secs > pow(2, 32)-1:
            logger.warning("Error: sleep_secs out of range")
            error_flag = True

        if not error_flag:
            # Split sleep_secs into four bytes
            _slptm_byte_3, _slptm_byte_2, _slptm_byte_1, _slptm_byte_0 = (sleep_secs & 0xFFFFFFFF).to_bytes(4, "big")

            # # Send all four bytes to their respective registers on the PIC Controller
            # self._bus.write_i2c_block_data(self._DEV_ADDR, self._SLPB0, [_slptm_byte_0])
            # time.sleep(.1)
            # self._bus.write_i2c_block_data(self._DEV_ADDR, self._SLPB1, [_slptm_byte_1])
            # time.sleep(.1)
            # self._bus.write_i2c_block_data(self._DEV_ADDR, self._SLPB2, [_slptm_byte_2])
            # time.sleep(.1)
            # self._bus.write_i2c_block_data(self._DEV_ADDR, self._SLPB3, [_slptm_byte_3])
            # time.sleep(.1)

            # Send all four bytes to their respective registers on the PIC Controller
            status = self._write_block_data(self._DEV_ADDR, self._SLPB0, [_slptm_byte_0])  # TODO: Implement Status usage
            status = self._write_block_data(self._DEV_ADDR, self._SLPB1, [_slptm_byte_1])  # TODO: Implement Status usage
            status = self._write_block_data(self._DEV_ADDR, self._SLPB2, [_slptm_byte_2])  # TODO: Implement Status usage
            status = self._write_block_data(self._DEV_ADDR, self._SLPB3, [_slptm_byte_3])  # TODO: Implement Status usage

        return error_flag

    def strobe(self, new_state):
        """Enable the Recovery Strobe

        Parameters
        ----------
        new_state : ENABLE or DISABLE

        Returns:
        --------
        none

        Example:
        --------
        from minion_hat import MinionHat
        min_hat = MinionHat()
        min_hat.strobe(min_hat.ENABLE)
        min_hat.strobe(min_hat.DISABLE)

        """
        # self._bus.write_i2c_block_data(self._DEV_ADDR, self._STRBEN, new_state)
        status = self._write_block_data(self._DEV_ADDR, self._STRBEN, new_state)  # TODO: Implement Status usage
        time.sleep(.1)

    def strobe_timing(self, t_on, t_off):
        """Configure the recovery strobe on and off timing.  At power-on-reset,
        the Minion Hat controller defaults to t_on = 100ms and t_off = 1900ms

        Parameters
        ----------
        t_on : strobe on time in milliseconds   (range: 0-65535)
        t_off : strobe off time in milliseconds (range: 0-65535)

        Returns:
        --------
        error_flag : False, No errors   True, error detected

        Example:
        --------
        from minion_hat import MinionHat
        min_hat = MinionHat()
        min_hat.strobe_timing(250, 1750) # 250ms on, 1725ms off

        """

        error_flag = False

        # Range Check
        if t_on < 0 or t_on > 65535:
            logger.warning("Error: t_on out of range")
            error_flag = True

        if t_off < 0 or t_off > 65535:
            logger.warning("Error: t_off out of range.")
            error_flag = True

        if not error_flag:

            # Split integer into bytes
            _on_hi_byte, _on_lo_byte = (t_on & 0xFFFF).to_bytes(2, "big")
            _off_hi_byte, _off_lo_byte = (t_off & 0xFFFF).to_bytes(2, "big")

            # self._bus.write_i2c_block_data(self._DEV_ADDR, self._STRBONH, [_on_hi_byte])
            # time.sleep(.1)
            # self._bus.write_i2c_block_data(self._DEV_ADDR, self._STRBONL, [_on_lo_byte])
            # time.sleep(.1)
            # self._bus.write_i2c_block_data(self._DEV_ADDR, self._STRBOFFH, [_off_hi_byte])
            # time.sleep(.1)
            # self._bus.write_i2c_block_data(self._DEV_ADDR, self._STRBOFFL, [_off_lo_byte])
            # time.sleep(.1)

            status = self._write_block_data(self._DEV_ADDR, self._STRBONH, [_on_hi_byte])  # TODO: Implement Status usage
            status = self._write_block_data(self._DEV_ADDR, self._STRBONL, [_on_lo_byte])  # TODO: Implement Status usage
            status = self._write_block_data(self._DEV_ADDR, self._STRBOFFH, [_off_hi_byte])  # TODO: Implement Status usage
            status = self._write_block_data(self._DEV_ADDR, self._STRBOFFL, [_off_lo_byte])  # TODO: Implement Status usage

        return error_flag

    def burn_wire(self, new_state):
        """Activate or Deactivate the burn wire

        Parameters
        ----------
        new_state : ON or OFF

        Returns:
        --------
        none

        Example:
        --------
        from minion_hat import MinionHat
        min_hat = MinionHat()
        min_hat.burn_wire(min_hat.ON)   # Activate the burn wire
        min_hat.burn_wire(min_hat.OFF)  # Deactivate the burn wire

        """
        # self._bus.write_i2c_block_data(self._DEV_ADDR, self._BRNWIRE, new_state)
        status = self._write_block_data(self._DEV_ADDR, self._BRNWIRE, new_state)  # TODO: Implement Status usage
        # time.sleep(.1)
