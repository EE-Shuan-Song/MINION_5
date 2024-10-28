from picamera2 import Picamera2, Preview
import time
import os
import logging

logging.basicConfig(filename='log_test.log',  # Log output file
                    filemode='a',  # append using 'a', overwrite using 'w'
                    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
                    level=logging.INFO)  # Log level

# Log a message: start!
logging.info("########################################################################")
logging.info("Program started successfully")
logging.info("########################################################################")

# try to delete existent test images
try:
    result = os.system('sudo rm /home/minion/test/*.jpg')
    # Check the result of the os.system() call
    if result == 0:
        logging.info("Files successfully deleted.")
    else:
        logging.warning("No files deleted, or an error occurred during deletion.")

except Exception as e:
    # Catch any other unexpected errors
    logging.error(f"An unexpected error occurred: {e}")

# now start to use Picamera2 to capture one test image
filename = '/home/minion/test/test02.jpg'

cam = Picamera2()
cam.configure(cam.create_still_configuration())
cam.start_preview(Preview.DRM)
cam.start()
time.sleep(5)
cam.capture_file(filename)
# test if the test image is captured
if os.path.exists(filename):
    logging.info("image captured successfully")
else:
    logging.info("image captured failed")

time.sleep(5)
cam.stop()

logging.info("Program finished")
