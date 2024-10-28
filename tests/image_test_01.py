from picamera2 import Picamera2, Preview
import time

filename = '/home/minion/test/test.jpg'

cam = Picamera2()
cam.configure(cam.create_still_configuration())
cam.start_preview(Preview.DRM)
cam.start()
time.sleep(5)
cam.capture_file(filename)
time.sleep(5)
cam.stop()
