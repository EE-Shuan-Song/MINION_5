from sensors.ds3231 import DS3231

_rtc_ext = DS3231()


# rewrote on 10/26/2024 by Yixuan
# no longer needs to call minion_toolbox
# simply run
# python rtc_setup.py

def rtc_ext_disp_time(**kwargs):
    """
    Read and Display the Date and Time from the DS3231 RTC.

    Keyword Args:
    -------------
    verbose : bool (default=True)
        If True, prints the Date and Time to the console.

    Returns:
    --------
    str : Date and Time String in the format YYYY/MM/DD hh:mm:ss
    """
    options = {'verbose': True}
    options.update(kwargs)

    time_str = _rtc_ext.disp_time(verbose=options['verbose'])

    if options['verbose']:
        print(f"Current Time: {time_str}")
    return time_str


def rtc_ext_set_time(**kwargs):
    """
    Set Date and Time on the DS3231 RTC.

    Keyword Args:
    -------------
    sync : bool (default=True)
        If True, synchronizes Raspberry Pi’s system clock with the DS3231.

    Returns:
    --------
    None
    """
    options = {'sync': True}
    options.update(kwargs)

    # Display the current time from RTC without printing
    now_time = rtc_ext_disp_time(verbose=False)
    print(f"\nDS3231 Current Date and Time: [{now_time}]")

    # Prompt user to enter a new time
    try:
        new_time = input("Enter a new date and time (YYYY/MM/DD hh:mm:ss): ").strip()
        if new_time:
            _rtc_ext.set_time(new_time)
            print(f"DS3231 RTC successfully updated to: {new_time}")
        else:
            print("No changes made to the RTC time.")
    except Exception as e:
        print(f"Error setting the RTC time: {str(e)}")

    # Synchronize system clock if requested
    if options['sync']:
        try:
            sync_system_clock()
        except Exception as e:
            print(f"Error syncing system clock: {str(e)}")


def sync_system_clock():
    """
    Synchronize Raspberry Pi's system clock with the DS3231 RTC.
    """
    rtc_time = rtc_ext_disp_time(verbose=False)

    # Synchronize system time using the 'date' command
    from subprocess import run
    run(["sudo", "date", "-s", rtc_time], check=True)
    print("System clock synchronized with DS3231 RTC.")


# Run the script
if __name__ == "__main__":
    print("1. Display current RTC time")
    print("2. Set new RTC time")
    choice = input("Select an option (1 or 2): ").strip()

    if choice == '1':
        rtc_ext_disp_time()
    elif choice == '2':
        rtc_ext_set_time()
    else:
        print("Invalid option. Please run the script again.")
