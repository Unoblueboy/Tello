class TelloException(Exception):
    """Exceptions raised by the Tello drone"""
    def __init__(self, message, command):
        super().__init__(message)
        self.command = command