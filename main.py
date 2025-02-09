import time
import logging

from tello.drone import TelloDrone

t = TelloDrone()

# t.command()
# print("speed", t.speed)
# print("battery", t.battery)
# print("time", t.time)
# print("height", t.height)
# print("temp", t.temperature)
# print("attitude", t.attitude)
# print("baro", t.barometer)
# print("acceleration", t.acceleration)
# print("tof", t.time_of_flight)
# print("wifi", t.wifi)
# print(t.state)

t.speed
t.battery
t.time
t.height
t.temperature
t.attitude
t.barometer
t.acceleration
t.time_of_flight
t.wifi
t.state

logging.basicConfig(filename='example.log', filemode='w', level=logging.DEBUG)

# while True:
#     # Continuously take off and land 
#     print("Begin Take Off")
#     print(t.takeoff(False))
#     print("Finish Take Off")
#     time.sleep(3)
#     print("Begin Land")
#     print(t.land(False))
#     print("End Land")
#     time.sleep(3)