# Imports
import smbus2 as smbus
import re
import os
import logging

# modified by Yixuan on 10/16/2024
# replace smbus by smbus2
# add logging functions
#
# updated on 10/23/2024
# use RTC to set up an alarm

logging.basicConfig(
    filename='log_test.log',  # Log output file
    filemode='a',  # Append to the file
    format='%(asctime)s - %(name)s - %(message)s',  # Log format (no log level)
    level=logging.INFO  # Log level
)

logger = logging.getLogger(__name__)
###### Log a message: start!
# logger.info("########################################################################")
# logger.info("DS3231 RTC called")
# logger.info("########################################################################")

# Pin Definitions
ALARM_PIN = 3


class DS3231(object):
    # the register value is the binary-coded decimal (BCD) format
    # sec min hour week day month year
    _wk_day = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    _address = 0x68
    _start_reg = 0x00
    _alarm1_reg = 0x07  # minutes, hour,... alarm1 start from 0x08
    _control_reg = 0x0e
    _status_reg = 0x0f

    _REG_SECONDS = 0x00
    _REG_MINUTES = 0x01
    _REG_HOURS = 0x02
    _REG_DAY = 0x03
    _REG_DATE = 0x04
    _REG_MONTH = 0x05
    _REG_YEAR = 0x06

    def __init__(self, _bus=1):
        self._bus: smbus.SMBus = None

        try:
            self._bus = smbus.SMBus(_bus)
        except:
            logger.warning(f"Bus {_bus} is not available. Available busses are listed as /dev/i2c*")
            if os.uname()[1] == 'raspberrypi':
                logger.warning("Enable the i2c interface using raspi-config!")

    def _int_to_bcd(self, data):
        """Converts integer data to bcd data for the DS3231 register format

        Parameters
        ----------
        int data : Integer data to be converted to BCD Format

        Returns:
        --------
        int bcd_data : BCD form of data

        Additional Notes:
        -----------------
        This method only converts a two-digit integer!  It was designed
        to format the data properly for the DS3231 registers.
        """
        bcd_data = int(str(data)[-2:], base=16)
        return bcd_data

    def _reg_write(self, data, reg_addr):
        """Writes data to a specified register via the I2C bus

        Parameters:
        ----------
        int data : Data to be written to the register
        int reg_addr = Register address to be written

        Returns:
        --------
        none

        common values:
        0x00 clear a register / reset a value
        0x05 enable alarm 1 interrupt
        0x80 set MSB bit to ignore day/date match in alarms
        search for DS3231 Register Map for more information

        """
        self._bus.write_byte_data(self._address, reg_addr, data)

    def set_time(self, new_time):
        """Set Date and Time on the DS3231 External RTC

        Parameters
        ----------
        str new_time : Formatted Date and Time String

        Returns:
        --------
        bool success : True if successful, False if an error occurred

        Additional Notes:
        -----------------
        This method accepts a formatted Date and time string in the form
        'YYYY/MM/DD hh:mm:ss'.  If the format is not correct, it will
        not be accepted. In addition, there is a range check for all
        fields.
        """
        format_check_flag = True
        success = False  # default state

        result = re.match('^[0-9][0-9][0-9][0-9]/[0-9][0-9]*/[0-9][0-9]\s[0-9][0-9]:[0-9][0-9]:[0-9][0-9]$', new_time)
        if result == None:
            format_check_flag = False
        else:
            format_check_flag = True
            regex = re.compile("[/: ]")
            date_time_list = regex.split(new_time)

            # Parse the fields (ascii)
            YYYY = date_time_list[0]
            YY = YYYY[-2:]  # 2-digit year
            MM = date_time_list[1]
            DD = date_time_list[2]
            hh = date_time_list[3]
            mm = date_time_list[4]
            ss = date_time_list[5]
            ww = '06'  # always Friday!

            # Prepend a 0 if month was entered as a single digit
            if len(MM) < 2:
                MM = '0' + MM

            # Check field ranges
            if int(YYYY) not in range(0, 3000):
                format_check_flag = False
                logger.warning("Year not in range")
            if int(MM) not in range(1, 12 + 1):
                format_check_flag = False
                logger.warning("Month not in range")
            if int(DD) not in range(1, 31 + 1):
                format_check_flag = False
                logger.warning("Day not in range")
            if int(hh) not in range(0, 23 + 1):
                format_check_flag = False
                logger.warning("Hours not in range")
            if int(mm) not in range(0, 59 + 1):
                format_check_flag = False
                logger.warning("Minutes not in range: " + str(mm))
            if int(ss) not in range(0, 59 + 1):
                format_check_flag = False
                logger.warning("Seconds not in range")

        if not format_check_flag:
            logger.warning('Incorrect format entry. Time not changed.')
            success = False
            return success
        else:
            pass
            #print(new_time)

        # Convert all values to BCD
        bcd_ss = self._int_to_bcd(int(ss))
        bcd_mm = self._int_to_bcd(int(mm))
        bcd_hh = self._int_to_bcd(int(hh))
        bcd_DD = self._int_to_bcd(int(DD))
        bcd_MM = self._int_to_bcd(int(MM))
        bcd_YYYY = self._int_to_bcd(int(YYYY))

        # Write the time / date
        self._reg_write(bcd_ss, self._REG_SECONDS)
        self._reg_write(bcd_mm, self._REG_MINUTES)
        self._reg_write(bcd_hh, self._REG_HOURS)
        self._reg_write(bcd_DD, self._REG_DATE)
        self._reg_write(bcd_MM, self._REG_MONTH)
        self._reg_write(bcd_YYYY, self._REG_YEAR)

        success = True
        return success

    def read_time(self):
        """Read the Date and Time from the DS3231 External RTC

        Parameters
        ----------
        none

        Returns:
        --------
        dict the_time : Date and Time Dictionary
            keys:
                str YYYY : Year
                str MM : Month
                str DD : Day
                str hh : Hours
                str mm : Minutes
                str ss : Seconds
        """

        keys = ['YYYY', 'MM', 'DD', 'hh', 'mm', 'ss', 'ww']
        the_time = dict.fromkeys(keys)

        t = self._bus.read_i2c_block_data(self._address, self._start_reg, 7)  #c-python
        #t = self._bus.readfrom_mem(int(self._address), int(self._start_reg), 7) #micropython

        the_time['YYYY'] = ("20%x" % (t[6])).ljust(4, '0')  # Assumes 20th Century!, pads zeros to the right
        the_time['MM'] = "%02x" % (t[5])
        the_time['DD'] = "%02x" % (t[4])
        the_time['ww'] = "%s" % (self._wk_day[t[3] - 1])
        the_time['hh'] = "%02x" % (t[2])
        the_time['mm'] = "%02x" % (t[1])
        the_time['ss'] = "%02x" % (t[0])

        # Print for testing purposes only!!! - Use disp_time()
        #print(the_time['YYYY'] + "/" + the_time["MM"] + "/" + the_time["DD"] + " " + the_time["hh"] + ":" + the_time['mm'] + ":" + the_time['ss'])
        return the_time

    def disp_time(self, **kwargs):
        """Read and Display the Date and Time from the DS3231 External RTC

        Keyword Args:
        -------------
        verbose : displays the Date and Time (default True)

        Returns:
        --------
        str time_str : Date and Time String in the format YYYY/MM/DD hh:mm:ss
            where:
                str YYYY : Year
                str MM : Month
                str DD : Day
                str hh : Hours
                str mm : Minutes
                str ss : Seconds

        Additional Notes:
        -----------------
        This method can display the date and time but the user can also
        suppress this feature and simply use the returned string in their
        desired formatting.
        """
        options = {
            'verbose': True
        }
        options.update(kwargs)

        now_time = self.read_time()

        YYYY = now_time['YYYY']
        MM = now_time['MM']
        DD = now_time['DD']
        hh = now_time['hh']
        mm = now_time['mm']
        ss = now_time['ss']
        ww = now_time['ww']

        # Compile the Date & Time into a formated string object
        time_str = "%s/%s/%s %s:%s:%s" % (YYYY, MM, DD, hh, mm, ss)

        # User can choose to disable the printing of time to the console by setting verbose = False
        if options['verbose'] == True:
            print(time_str)

        return time_str

    def set_alarm_in_min(self, minutes):
        """Set Alarm 1 to trigger after a given number of minutes."""
        current_time = self.read_time()

        # Calculate future time (minutes + offset)
        new_minute = (int(current_time['mm'], 16) + minutes) % 60
        new_hour = int(current_time['hh'], 16) + (int(current_time['mm'], 16) + minutes) // 60

        # Convert to BCD format
        bcd_new_minute = self._int_to_bcd(new_minute)
        bcd_new_hour = self._int_to_bcd(new_hour % 24)

        # Write to Alarm 1 registers (starting at 0x07)
        self._reg_write(0x00, self._alarm1_reg)  # Alarm 1 seconds (ignored)
        self._reg_write(bcd_new_minute, self._alarm1_reg + 1)  # Alarm 1 minutes (0x08)
        self._reg_write(bcd_new_hour, self._alarm1_reg + 2)  # Alarm 1 hours (0x09)
        self._reg_write(0x80, self._alarm1_reg + 3)  # Set "don't care" for day (0x0A)

        # Enable Alarm 1 with interrupt in control register (0x0E)
        self._reg_write(0x05, self._control_reg)  # Enable Alarm 1 interrupt and output
