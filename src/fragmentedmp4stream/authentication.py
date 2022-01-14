"""HTTP Authentication: Basic and Digest Access Authentication"""
import abc
import base64
import random
import string
from hashlib import md5


class AuthenticationException(Exception):
    """Class for Authentication exceptions"""
    def __init__(self, message: str) -> None:
        self._message = message

    def __repr__(self) -> str:
        return self._message


class AuthenticationContainer:
    """Authentication container for both basic and digest modes"""
    def __init__(self, basic_settings: str, digest_settings: str):
        self._basic, self._digest = None, None
        if basic_settings:
            self._basic = BasicAuthentication(basic_settings)
        if digest_settings:
            self._digest = DigestAuthentication(digest_settings)

    def verify(self, header: list, method: str) -> None:
        """Check Authorization header for current mode"""
        if header:
            settings = header[0].split(' ')
            if settings[1] == 'Basic' and self._basic:
                return self._basic.verify(settings)
            elif settings[1] == 'Digest' and self._digest:
                return self._digest.verify(settings, method)

        www_authenticate_header = ''
        if self._basic:
            www_authenticate_header += f'WWW-Authenticate: {self._basic.header()}'
        if self._digest:
            www_authenticate_header += f'WWW-Authenticate: {self._digest.header()}'
        if www_authenticate_header:
            raise AuthenticationException(f'RTSP/1.0 401 Unauthorized\r\n{www_authenticate_header}')


class Authentication:
    """Base class of HTTP Authentication"""
    def __init__(self, settings: str) -> None:
        self.credentials, self.realm = settings.split('@')

    @abc.abstractmethod
    def header(self) -> str:
        """Check Authorization header"""
        return ''


class BasicAuthentication(Authentication):
    """Basic HTTP Authentication"""
    def __init__(self, credentials: str) -> None:
        super().__init__(credentials)

    def header(self) -> str:
        """Get Authentication header"""
        return f'Basic realm=\"{self.realm}\"\r\n'

    def verify(self, settings: list) -> None:
        """Check Authorization header"""
        if len(settings) != 3 or settings[1] != 'Basic':
            raise AuthenticationException('RTSP/1.0 472 Failure to Establish Secure Connection\r\n')
        if base64.b64decode(settings[2].encode()).decode() != self.credentials:
            raise AuthenticationException('RTSP/1.0 471 Connection Credentials Not Accepted\r\n')


class DigestAuthentication(Authentication):
    """Digest HTTP Authentication"""

    def __init__(self, credentials: str) -> None:
        super().__init__(credentials)
        username, password = self.credentials.split(':')
        self.a_first = md5((username + ':' + self.realm + ':' + password).encode('utf-8')).hexdigest()
        source = string.ascii_letters + string.digits
        self._nonce = ''.join(map(lambda x: random.choice(source), range(10)))

    def header(self) -> str:
        """Get Authentication header"""
        return f'Digest realm=\"{self.realm}\",nonce=\"{self._nonce}\"\r\n'

    def verify(self, settings: list, method: str) -> None:
        """Check Authorization header"""
        if len(settings) < 2 or settings[1] != 'Digest':
            raise AuthenticationException('RTSP/1.0 472 Failure to Establish Secure Connection\r\n')
        a_second, c_nonce, response = '', '', ''
        for s in settings:
            if 'uri=' in s:
                a_second = md5((method + ':' + s.split('"')[1]).encode('utf-8')).hexdigest()
            elif 'nonce=' in s:
                c_nonce = s.split('"')[1]
            elif 'response=' in s:
                response = s.split('"')[1]
        digest = md5((self.a_first + ':' + c_nonce + ':' + a_second).encode('utf-8')).hexdigest()
        if digest != response:
            raise AuthenticationException('RTSP/1.0 471 Connection Credentials Not Accepted\r\n')
