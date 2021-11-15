"""HTTP Authentication: Basic and Digest Access Authentication"""
import abc
import base64


class AuthenticationException(Exception):
    """Class for Authentication exceptions"""
    def __init__(self, message: str) -> None:
        self._message = message

    def __repr__(self) -> str:
        return self._message


class Authentication:
    """Base class of HTTP Authentication"""

    @staticmethod
    def make(settings: str):
        return BasicAuthentication(settings)

    def __init__(self, settings: str) -> None:
        self.credentials, self.realm = settings.split('@')

    @abc.abstractmethod
    def verify(self, header: list) -> None:
        """Check Authorization header"""


class BasicAuthentication(Authentication):
    """Basic HTTP Authentication"""
    def __init__(self, credentials: str) -> None:
        super().__init__(credentials)

    def verify(self, header: list) -> None:
        """Check Authorization header"""
        if not header:
            raise AuthenticationException(f'RTSP/1.0 401 Unauthorized\r\n'
                                          f'WWW-Authenticate: Basic realm=\"{self.realm}\"\r\n')
        settings = header[0].split(' ')
        if len(settings) != 3 or settings[1] != 'Basic':
            raise AuthenticationException('RTSP/1.0 472 Failure to Establish Secure Connection\r\n')
        if base64.b64decode(settings[2].encode()).decode() != self.credentials:
            raise AuthenticationException('RTSP/1.0 471 Connection Credentials Not Accepted\r\n')
