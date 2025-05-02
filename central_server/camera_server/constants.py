from ..socket_server_lib.constants import Options

class Constants:
    DISCOVER_CAMERA_QUERY_PORT = 5000
    DISCOVER_CAMERA_RESPONSE_PORT = 5001
    CAMERA_LINK_PORT = 5002
    CAMERA_COMMS_PORT = 4999

class Messages:
    class CameraLink:
        SERVER_LINK_SYN = [b"CAMLINK-HSEC", Options.ANY_VALUE_TEMPLATE]
        CLIENT_LINK_ACK = [b"CAMACK-HSEC"]
        SERVER_KEY_VALDIATION = [b"CAMKEY-HSEC", Options.ANY_VALUE_TEMPLATE]
        CAMERA_LINK_SUCCESS = [b"CAMOK-HSEC", Options.ANY_VALUE_TEMPLATE]
    
    class LastFrame:
        SERVER_QUERY = [b"LAST"]
        CLIENT_RES = [b"LAST", Options.ANY_VALUE_ANY_LENGTH_TEMPLATE]
    
    class Streaming:
        SERVER_QUERY = [b"STREAM"]
        CLIENT_RES = [b"FRAME", Options.ANY_VALUE_ANY_LENGTH_TEMPLATE]
        
        