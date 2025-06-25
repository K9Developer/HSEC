from ..socket_server_lib.constants import Options

CATEGORY_TO_CLASS = {
    "People": ["person"],
    "Vehicles": ["bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat"],
    "Animals": ["bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe"],
}

class Constants:
    CAMERA_HEARTBEAT_LISTENER_PORT = 5000
    CAMERA_HANDLER_PORT = 5001
    SERVER_COMMS_PORT = 5002

    CAMERA_MAC_PREFIX = "12:34:56"

    STATIC_CAMERA_FRAME_UPDATE_INTERVAL = 30
    
    RED_ZONE_DETECTION_THRESHOLD = 50
    FRAMES_BETWEEN_RED_ZONE_CHECKS = 20
    
    TIMELAPSE_FPS = 5
    TIMELAPSE_CHUNK_DURATION = 5 # seconds

class Messages:
    CAMERA_PAIRING_QUERY = [b"CAMPAIR-HSEC", Options.ANY_VALUE_TEMPLATE]
    CAMERA_PAIRING_RESPONSE = [b"CAMACK-HSEC", Options.ANY_VALUE_TEMPLATE, Options.ANY_VALUE_TEMPLATE]
    CAMERA_UNPAIR_REQUEST = [b"CAMUNPAIR-HSEC"]

    CAMERA_WRONG_CODE = [b"BADCODE-HSEC", Options.ANY_VALUE_TEMPLATE]

    CAMERA_PAIR_REQUEST = [b"CAMLINK-HSEC", Options.ANY_VALUE_TEMPLATE]
    CAMERA_REPAIR_REQUEST = [b"CAMRELINK-HSEC", Options.ANY_VALUE_TEMPLATE]
    
    CAMERA_REPAIR_CONFIRM = [b"CAMREPAIR-HSEC", Options.ANY_VALUE_TEMPLATE]
    CAMERA_REPAIR_CONFIRM_ACK = [b"CAMREPAIRACK-HSEC", Options.ANY_VALUE_TEMPLATE]

    CAMERA_FRAME = [b"CAMFRAME-HSEC", Options.ANY_VALUE_ANY_LENGTH_TEMPLATE]
