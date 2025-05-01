import enum

class ServerProtocol(enum.Enum):
    TCP = "tcp"
    UDP = "udp"

class SocketServerCallbacks(enum.Enum):
    ON_BEFORE_CONNECT = "on_before_connect"
    ON_CONNECT = "on_connect"
    ON_DISCONNECT = "on_disconnect"
    UNRECOGNIZED_MESSAGE = "unrecognized_message"
    CLIENT_ERROR = "client_error"
    CLIENT_MESSAGE = "client_message"

    NO_CALLBACK = "no_callback"

class DataTransferOptions(enum.Flag):
    WITH_SIZE = enum.auto()
    ENCRYPT_AES = enum.auto()
    IS_PATTERN = enum.auto() # behind the scenes only

class Options(enum.Enum):
    MESSAGE_SIZE_BYTE_LENGTH = 4
    MESSAGE_SEPARATOR = b"\0"
    ANY_VALUE_TEMPLATE = b"\0"

# \0 in a field means any value
class SocketMessages:
    class AesKeyExchange:
        SERVER_HELLO = [b"exch", b"rsa", b"aes"]
        CLIENT_HELLO = [b"exch", b"rsa",  b"aes", Options.ANY_VALUE_TEMPLATE]
        SERVER_KEY_EXCHANGE = [b"exch", b"rsa", b"aes", Options.ANY_VALUE_TEMPLATE]
        CLIENT_KEY_CONFIRM = [Options.ANY_VALUE_TEMPLATE]