import sqlite3

class Camera:
    def __init__(self, mac, name, last_frame, key, red_zone, ip):
        self.mac = mac
        self.name = name
        self.last_frame = last_frame
        self.key = key
        self.red_zone = red_zone
        self.ip = ip

    def __repr__(self):
        return f"Camera(mac={self.mac}, name={self.name}, last_frame={self.last_frame}, key={self.key})"

class CameraDatabase:
    def __init__(self, db_path='cameras.db'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cameras (
                mac TEXT PRIMARY KEY,
                name TEXT,
                last_frame TEXT,
                key TEXT,
                red_zone TEXT,
                last_known_ip TEXT
            )
        ''')
        self.conn.commit()

    def add_camera(self, mac, name, key, ip):
        self.cursor.execute('''
            INSERT OR REPLACE INTO cameras (mac, name, last_frame, key, red_zone, last_known_ip)
            VALUES (?, ?, ?, ?)
        ''', (mac, name, None, key, None, ip))
        self.conn.commit()

    def get_camera(self, mac):
        self.cursor.execute('''
            SELECT * FROM cameras WHERE mac = ?
        ''', (mac,))
        row = self.cursor.fetchone()
        return Camera(*row) if row else None

    def rename_camera(self, mac, new_name):
        self.cursor.execute('''
            UPDATE cameras SET name = ? WHERE mac = ?
        ''', (new_name, mac))
        self.conn.commit()

    def get_all_cameras(self):
        self.cursor.execute('''
            SELECT * FROM cameras
        ''')
        return [Camera(*row) for row in self.cursor.fetchall()]

    def update_camera(self, mac, last_frame):
        self.cursor.execute('''
            UPDATE cameras SET last_frame = ? WHERE mac = ?
        ''', (last_frame, mac))
        self.conn.commit()

    def set_red_zone(self, mac, red_zone):
        self.cursor.execute('''
            UPDATE cameras SET red_zone = ? WHERE mac = ?
        ''', (red_zone, mac))
        self.conn.commit()

    def close(self):
        self.conn.close()
