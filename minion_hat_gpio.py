import atexit
import logging
from threading import Thread
from time import sleep, time
from RPi import GPIO
from minion_hat_i2c import MinionHat

min_hat = MinionHat()

# created and modified by Yixuan on 10/16/2024
# different from Minion_hat, this file does not focus on the I2C communication.
# It completes the gpio registration.
# For our Minion use, I also added the Blue LED here to have all LED controls written in this sub function.
# It partially follows Nils' minion_hat_gpio.py
# rewrote a few sub functions here and added the OXYBASE, ARDUCAM relevant gpio configurations

logging.basicConfig(
    filename='log_test.log',  # Log output file
    filemode='a',  # Append to the file
    format='%(asctime)s - %(name)s - %(message)s',  # Log format (no log level)
    level=logging.INFO  # Log level
)
logger = logging.getLogger(__name__)

# Pin configuration (directly connected to pi through minion_hat)
LED_GREEN = 29
LED_RED = 32
LED_RING = 13
OXYBASE_EN = 12
ARDUCAM_SEL = 7
ARDUCAM_OE = 11


def init():
    """
    Setup pin direction
    """
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(LED_RING, GPIO.OUT)
    GPIO.setup(LED_GREEN, GPIO.OUT)
    GPIO.setup(LED_RED, GPIO.OUT)
    GPIO.setup(OXYBASE_EN, GPIO.OUT)
    GPIO.setup(ARDUCAM_SEL, GPIO.OUT)
    GPIO.setup(ARDUCAM_OE, GPIO.OUT)


def cleanup():
    GPIO.cleanup()


def led_green(new_state: bool):
    """
    Enable or disable the green LED on hat

    Parameters
    ----------
    new_state : True (on) or False (off)
    """
    GPIO.output(LED_GREEN, GPIO.HIGH if new_state else GPIO.LOW)


def led_red(new_state: bool):
    """
    Enable or disable the red LED on hat

    Parameters
    ----------
    new_state : True (on) or False (off)

    Returns
    -------
    None
    """
    GPIO.output(LED_RED, GPIO.HIGH if new_state else GPIO.LOW)


def led_blue(new_state: bool):
    """
    Enable or disable the blue LED on hat
    Different from red and green LEDs, this one uses I2C communication, so Minion_Hat is called.

    Parameters
    ----------
    new_state : True (on) or False (off)

    Returns
    -------
    None
    """
    state = min_hat.ON if new_state else min_hat.OFF
    min_hat.led(state)


# ----------------------------------------------------------------------------------------------------------------------
# Light Ring Control
# ----------------------------------------------------------------------------------------------------------------------

# Use module with functions instead of class to provide a singleton pattern (simplest way in python)

# Safety Parameters
LIGHT_RING_MAX_ON_TIME = 60  # seconds
LIGHT_RING_MIN_OFF_TIME = 5  # seconds
LIGHT_RING_REFRESH_DELAY = 0.5  # seconds
# States variables
ring_state: bool = False  # tracks if light ring is on or off
ring_on_time: float = 0  # tracks the cumulative time the light ring has been on
ring_off_time: float = LIGHT_RING_MIN_OFF_TIME  # tracks the time it has been off
ring_flashing: bool = False  # whether the light ring is flashing
ring_flash_count: int = 0  # number of flashes
ring_flash_on_time: int = 250  # ms for flash on
ring_flash_off_time: int = 250  # ms for flash off
ring_alive: bool = False  # whether the light ring thread is active
ring_thread: Thread = None  # reference to the thread for the light ring
flash_counter: int = 0  # Track the number of flashes completed


def light_ring_set(new_state: bool):
    """
    Set the state of the LightRing
    Safety only works if refresh_delay is smaller than the on/off times of led

    Parameters
    ----------
    new_state : True (on) or False (off)

    Returns
    -------
    None
    """
    global ring_state

    if ring_state == new_state:
        logger.debug(f'No change in state: {new_state}')
        return  # Nothing to do

    elif new_state:  # Turn on, only if light was off long enough
        if ring_off_time < LIGHT_RING_MIN_OFF_TIME:
            logger.warning('Min off time not met. Keeping LED ring off.')
            return  # Keep off

    # else: Can always turn off
    if not ring_alive:  # check if the thread is running
        light_ring_open_thread()  # start the thread

    GPIO.output(LED_RING, GPIO.HIGH if new_state else GPIO.LOW)
    ring_state = new_state


def light_ring_flash_set(count: int = 2, time_on: int = 250, time_off: int = 250):
    """
    Flash the LED Ring (non-blocking function)

    Parameters
    ----------
    count : number of flashes
    time_on : Flash on time in milliseconds
    time_off : Flash off time milliseconds

    Returns
    --------
    None

    Example: Generate 2 flashes, 250ms on time, 250ms off time (default; connected to WiFi)

        light_ring_flash_set(2,250,250)

    Example: Simply illuminates the LED Ring for 2 seconds

        light_ring_flash_set(1,2000,0)

    Example: Dimmable Setting --> quick on and off

        light_ring_flash_set(100,5,5)  # Dim by 50%

    """
    global ring_flash_count, ring_flash_on_time, ring_flash_off_time, ring_flashing, flash_counter

    # Handle overlapping flash requests: Stop the current sequence if flashing is active
    if ring_flashing:
        logger.info("New flash command received. Restarting flash sequence.")
        ring_flashing = False  # Stop the current flashing sequence

    # set new flash parameters and reset the counter
    ring_flash_count = count
    ring_flash_on_time = time_on
    ring_flash_off_time = time_off
    flash_counter = 0  # reset the flash counter
    ring_flashing = True

    if not ring_alive:
        light_ring_open_thread()


def light_ring_open_thread():
    global ring_alive, ring_thread
    ring_alive = True
    ring_thread = Thread(name=__name__ + '.LightRing', target=light_ring_run_thread)
    ring_thread.daemon = True
    ring_thread.start()


def light_ring_close_thread():
    """
    Turn off light ring and stop thread
    Returns
    -------
    """
    global ring_alive
    ring_alive = False
    GPIO.output(LED_RING, GPIO.LOW)


def light_ring_run_thread():
    global ring_alive, ring_thread, ring_on_time, ring_off_time, ring_flashing, \
        ring_flash_count, ring_flash_on_time, ring_flash_off_time, flash_counter

    start_time = time()

    while ring_alive:
        # Update safety timers
        if ring_state:
            ring_on_time += LIGHT_RING_REFRESH_DELAY
            ring_off_time = 0
        else:
            ring_on_time = 0
            ring_off_time += LIGHT_RING_REFRESH_DELAY

        # Safety check
        if ring_state and ring_on_time >= LIGHT_RING_MAX_ON_TIME:
            light_ring_set(False)
            logger.warning('Max "on" time reached. Turning off light ring.')

        # Flashing logic if flashing is active
        if ring_flashing:
            if flash_counter < ring_flash_count:
                GPIO.output(LED_RING, GPIO.HIGH)
                sleep(ring_flash_on_time / 1000)  # On time in seconds
                GPIO.output(LED_RING, GPIO.LOW)
                sleep(ring_flash_off_time / 1000)  # Off time in seconds
                flash_counter += 1
            else:
                # Stop flashing after completing the specified count
                ring_flashing = False
                flash_counter = 0  # Reset counter

        # Wait; save power and ensure the loop sleeps for some amount of time
        delta = LIGHT_RING_REFRESH_DELAY - (time() - start_time)
        if delta > 0.05 and ring_alive:
            sleep(delta)
            start_time = time()


"""
Serial Port Power (OxyBase)
"""


def oxybase_enable(new_state: bool):
    """
    Enable or disable the oxygen sensor (same as Nils' serial power)

    Parameters
    ----------
    new_state : True (on) or False (off)
    """
    GPIO.output(OXYBASE_EN, GPIO.HIGH if new_state else GPIO.LOW)


"""
ARDUCAM_SEL & ARDUCAM_OE
"""


def arducam_sel_enable(new_state: bool):
    """
    Enable or disable the arducam_sel

    Parameters
    ----------
    new_state : True (on) or False (off)
    """
    GPIO.output(ARDUCAM_SEL, GPIO.HIGH if new_state else GPIO.LOW)


def arducam_oe_enable(new_state: bool):
    """
    Enable or disable the arducam_oe

    Parameters
    ----------
    new_state : True (on) or False (off)
    """
    GPIO.output(ARDUCAM_OE, GPIO.HIGH if new_state else GPIO.LOW)


"""
Turn Off Power on Exit
"""


def power_off(keep_hat_leds_on: bool = True):
    try:
        logger.info("Shutting down: Closing LED ring thread.")
        light_ring_close_thread()

        logger.info("Shutting down: Turning off serial port power for oxygen sensor.")
        oxybase_enable(False)

        if not keep_hat_leds_on:
            logger.info("Turning off all other LEDs.")
            led_green(False)
            led_red(False)

        logger.info("Cleaning up GPIO resources.")
        cleanup()
    except RuntimeError as e:
        logger.warning(f"Error during power off: {e}")


atexit.register(power_off)
