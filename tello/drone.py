import socket
import threading
import logging

from tello.exception import TelloException
from tello.state import TelloState
from tello.generic import TemperatureRange, RotationVector, Vector

client_logger = logging.getLogger(f"{__name__}..client")
state_logger = logging.getLogger(f"{__name__}.state")
general_logger = logging.getLogger(__name__)

class TelloDrone:
    """Class representing the Tello drone"""

    DRONE_ADDRESS = ("192.168.10.1", 8889)
    BASE_TIMEOUT = 1.0

    def __init__(self):
        # Setup client socket for issuing and receicing commands
        self._client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._client_socket.bind(("0.0.0.0", 9000))
        self._client_socket.settimeout(TelloDrone.BASE_TIMEOUT)

        self._client_socket_lock = threading.Lock()

        # Setup a thread and socket to constantly receive full Tello State
        self.state_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.state_socket.bind(("0.0.0.0", 8890))

        self.state_thread = threading.Thread(target=self.state_thread_function)
        self.state_lock = threading.Lock()

        # set state variable to None
        self._state = None

        # Setup thread for constantly receiving video stream
        self.stream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.stream_socket.bind(("0.0.0.0", 11111))

        # Start Listening Threads
        self.state_thread.start()

    @property
    def state(self):
        """The state of the Tello drone"""
        with self.state_lock:
            return self._state
        
    @state.setter
    def state(self, value: TelloState):
        with self.state_lock:
            self._state=value

    @property
    def speed(self):
        """Get current speed (cm/s)"""
        general_logger.info("Get speed")
        byte_data = self._simple_client_socket_caller("speed?")
        stripped_data = byte_data.strip()
        return float(stripped_data)
    
    @property
    def battery(self):
        """Get current battery percentage"""
        return float(self._simple_client_socket_caller("battery?"))
    
    @property
    def time(self):
        """Get current fly time (s)"""
        byte_data = self._simple_client_socket_caller("time?")
        stripped_data = byte_data.strip()
        return int(stripped_data[:-1])
    
    @property
    def height(self):
        """Get height (cm)"""
        byte_data = self._simple_client_socket_caller("height?")
        stripped_data = byte_data.strip()
        return int(stripped_data[:-2])
    
    @property
    def temperature(self):
        """Get temperature range (°C)"""
        byte_data = self._simple_client_socket_caller("temp?")
        stripped_data = byte_data.strip()
        split_data = stripped_data.split(b"~")
        return TemperatureRange(int(split_data[0]),int(split_data[1][:-1]))
    
    @property
    def attitude(self):
        """Get IMU attitude data: roll, pitch, yaw"""
        byte_data = self._simple_client_socket_caller("attitude?")
        stripped_data = byte_data.strip()
        split_data = stripped_data.split(b";")
        return RotationVector(
            float(split_data[0][6:]),
            float(split_data[1][5:]),
            float(split_data[2][4:]))
    
    @property
    def barometer(self):
        """Get barometer value"""
        return float(self._simple_client_socket_caller("baro?"))
    
    @property
    def acceleration(self):
        """Get IMU angular acceleration data (0.001g)"""
        byte_data = self._simple_client_socket_caller("acceleration?")
        stripped_data = byte_data.strip()
        split_data = stripped_data.split(b";")
        return Vector[float](
            float(split_data[0][4:]),
            float(split_data[1][4:]),
            float(split_data[2][4:]))

    @property
    def time_of_flight(self):
        """Get Distance value from TOF (mm)"""
        byte_data = self._simple_client_socket_caller("tof?")
        stripped_data = byte_data.strip()
        return float(stripped_data[:-2])
    
    @property
    def wifi(self):
        """Get Wi-Fi signal to noise ratio (SNR)"""
        return int(self._simple_client_socket_caller("wifi?"))
    
    def _simple_client_socket_caller(self, command: str, bufsize: int = 2048, timeout=None):
        with self._client_socket_lock:
            byte_command = command.encode(encoding="utf8")
            if timeout is not None:
                self._client_socket.settimeout(timeout)
            self._client_socket.sendto(byte_command, TelloDrone.DRONE_ADDRESS)
            byte_data = self._client_socket.recv(bufsize)
            if timeout is not None:
                self._client_socket.settimeout(TelloDrone.BASE_TIMEOUT)
            return byte_data
    
    def _generic_client_socket_caller(
            self, 
            command: str, 
            bufsize: int = 2048,
            timeout: int = None,
            tries: int = 1,
            throw_exception: bool = True):
        try_num = 1
        while try_num <= tries:
            try:
                byte_data = self._simple_client_socket_caller(command, bufsize, timeout)
                print(command, byte_data)
                stripped_data = byte_data.strip()
                if stripped_data == b'ok':
                    return True
                elif throw_exception:
                    str_exception = stripped_data.decode(encoding="utf-8")
                    raise TelloException(str_exception, command)
                
            except Exception as exc:
                if throw_exception and try_num == tries:
                    raise exc
                elif try_num == tries:
                    return False
            try_num += 1
        return False

    def command(self):
        """Enter SDK Mode"""
        return self._generic_client_socket_caller("command")

    def takeoff(self, throw_exception = True, tries=3):
        """Tello auto takeoff"""
        return self._generic_client_socket_caller(
            "takeoff",
            throw_exception=throw_exception,
            tries=tries,
            timeout=5.0)

    def land(self, throw_exception = True, tries=3):
        """Tello auto land"""
        return self._generic_client_socket_caller(
            "land",
            throw_exception=throw_exception,
            tries=tries,
            timeout=5.0)

    def state_thread_function(self):
        while True:
            try:
                data = self.state_socket.recv(2048)
                string_data = data.decode(encoding="utf-8").strip()
                split_data = string_data.split(";")                
                self.state = TelloState(
                    RotationVector(
                        float(split_data[0][6:]),
                        float(split_data[1][5:]),
                        float(split_data[2][4:])),
                    Vector[int](
                        int(split_data[3][4:]),
                        int(split_data[4][4:]),
                        int(split_data[5][4:])),
                    TemperatureRange(
                        int(split_data[6][6:]),
                        int(split_data[7][6:])),
                    int(split_data[8][4:]),
                    int(split_data[9][2:]),
                    int(split_data[10][4:]),
                    float(split_data[11][5:]),
                    int(split_data[12][5:]),
                    Vector[float](
                        float(split_data[13][4:]),
                        float(split_data[14][4:]),
                        float(split_data[15][4:])))
                # print(self.state)
            except Exception as e:
                print(e)