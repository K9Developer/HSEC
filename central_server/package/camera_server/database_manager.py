import sqlite3
import threading

from package.socket_server_lib.client import SocketClient

class Camera:
    def __init__(self, mac, name, last_frame, key, red_zone, last_known_ip):
        self.mac = mac
        self.name = name
        self.last_frame = last_frame
        self.key = key
        self.red_zone = red_zone
        self.last_known_ip = last_known_ip
        self.client: SocketClient | None = None

    def __repr__(self):
        return f"Camera(mac={self.mac}, name={self.name}, last_frame={self.last_frame}, key={self.key})"

class CameraDatabase:
    def __init__(self, db_path='cameras.db'):
        self.db_path = db_path
        self.local = threading.local()
        self._init_main_thread()

    def _get_conn(self):
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.cursor = self.local.conn.cursor()
        return self.local.conn, self.local.cursor

    def _init_main_thread(self):
        conn, cursor = self._get_conn()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cameras (
                mac TEXT PRIMARY KEY,
                name TEXT,
                last_frame TEXT,
                key TEXT,
                red_zone TEXT,
                last_known_ip TEXT
            )
        ''')
        conn.commit()

    def remove_camera(self, mac):
        conn, cursor = self._get_conn()
        cursor.execute('DELETE FROM cameras WHERE mac = ?', (mac,))
        conn.commit()

    def add_camera(self, mac, name, key, last_known_ip):
        conn, cursor = self._get_conn()
        cursor.execute('''
            INSERT OR REPLACE INTO cameras (mac, name, last_frame, key, red_zone, last_known_ip)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (mac, name, None, key, None, last_known_ip))
        conn.commit()
        return Camera(mac, name, None, key, None, last_known_ip)

    def get_camera(self, mac):
        _, cursor = self._get_conn()
        cursor.execute('SELECT * FROM cameras WHERE mac = ?', (mac,))
        row = cursor.fetchone()
        return Camera(*row) if row else None

    def rename_camera(self, mac, new_name):
        conn, cursor = self._get_conn()
        cursor.execute('UPDATE cameras SET name = ? WHERE mac = ?', (new_name, mac))
        conn.commit()

    def get_all_cameras(self):
        _, cursor = self._get_conn()
        cursor.execute('SELECT * FROM cameras')
        return [Camera(*row) for row in cursor.fetchall()]

    def update_camera(self, mac, last_frame):
        conn, cursor = self._get_conn()
        cursor.execute('UPDATE cameras SET last_frame = ? WHERE mac = ?', (last_frame, mac))
        conn.commit()

    def update_camera_ip(self, mac, last_known_ip):
        conn, cursor = self._get_conn()
        cursor.execute('UPDATE cameras SET last_known_ip = ? WHERE mac = ?', (last_known_ip, mac))
        conn.commit()

    def set_red_zone(self, mac, red_zone):
        conn, cursor = self._get_conn()
        cursor.execute('UPDATE cameras SET red_zone = ? WHERE mac = ?', (red_zone, mac))
        conn.commit()

    def close(self):
        if hasattr(self.local, 'conn'):
            self.local.conn.close()
            del self.local.conn
            del self.local.cursor
