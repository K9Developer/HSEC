import sqlite3
import threading
from package.client_handler_server.constants import SESSION_ID_VALIDITY_DURATION
import os
import datetime
import hashlib

class User:
    def __init__(self, websocket, session_id, linked_cameras):
        self.websocket = websocket
        self.session_id = session_id
        self.is_connected = True
        self.streaming_camera = None # will be set to mac
        self.linked_cameras = linked_cameras.split(',') if linked_cameras else []


class UserDatabase:
    def __init__(self, db_path='users.db'):
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
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                password_hash TEXT,
                active_session_id TEXT,
                session_expiry INTEGER,
                linked_cameras TEXT DEFAULT '',
                salt TEXT DEFAULT ''
            )
        ''')
        conn.commit()

    def generate_session_id(self):
        return os.urandom(32).hex(), int(datetime.datetime.now(datetime.timezone.utc).timestamp()) + SESSION_ID_VALIDITY_DURATION

    def __generate_salt(self):
        return os.urandom(16).hex()

    def __hash_password(self, password, salt):
        return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

    def add_user(self, email, psw):
        conn, cursor = self._get_conn()
        sess, expiry = self.generate_session_id()
        salt = self.__generate_salt()
        password_hash = self.__hash_password(psw, salt)
        print(f"Password for {email}: {psw} + {salt}")
        cursor.execute('''
            INSERT OR REPLACE INTO users (email, password_hash, active_session_id, session_expiry, linked_cameras, salt)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (email, password_hash, sess, expiry, '', salt))
        conn.commit()
        return sess, expiry
    
    def get_salt(self, email):
        _, cursor = self._get_conn()
        cursor.execute('SELECT salt FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        if row:
            return row[0]
        return self.__generate_salt()

    def is_logged_in(self, email, session_id):
        conn, cursor = self._get_conn()
        cursor.execute('SELECT * FROM users WHERE email = ? AND active_session_id = ? AND session_expiry > ?', (email, session_id, int(datetime.datetime.now(datetime.timezone.utc).timestamp())))
        row = cursor.fetchone()
        if row:
            return True
        return False
    
    def get_user(self, email):
        _, cursor = self._get_conn()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        return User(row[0], row[2], row[4]) if row else None

    def is_correct_password(self, email, password_hash):
        _, cursor = self._get_conn()
        cursor.execute('SELECT * FROM users WHERE email = ? AND password_hash = ?', (email, password_hash))
        row = cursor.fetchone()
        if row:
            return True
        return False
    
    def update_session_id(self, email):
        conn, cursor = self._get_conn()
        sess, expiry = self.generate_session_id()
        cursor.execute('UPDATE users SET active_session_id = ?, session_expiry = ? WHERE email = ?', (sess, expiry, email))
        conn.commit()
        return sess, expiry
    
    def add_linked_camera(self, email, camera_mac):
        conn, cursor = self._get_conn()
        cursor.execute('SELECT linked_cameras FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        if row:
            linked_cameras = row[0].split(',') if row[0] else []
            if camera_mac not in linked_cameras:
                linked_cameras.append(camera_mac)
                cursor.execute('UPDATE users SET linked_cameras = ? WHERE email = ?', (','.join(linked_cameras), email))
                conn.commit()
                return True
        return False

    def remove_linked_camera(self, email, camera_mac):
        conn, cursor = self._get_conn()
        cursor.execute('SELECT linked_cameras FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        if row:
            linked_cameras = row[0].split(',') if row[0] else []
            if camera_mac in linked_cameras:
                linked_cameras.remove(camera_mac)
                cursor.execute('UPDATE users SET linked_cameras = ? WHERE email = ?', (','.join(linked_cameras), email))
                conn.commit()
                return True
        return False
    
    def get_linked_cameras(self, email):
        _, cursor = self._get_conn()
        cursor.execute('SELECT linked_cameras FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        if row:
            return row[0].split(',') if row[0] else []
        return []
    
    def get_users_using_camera(self, camera_mac):
        _, cursor = self._get_conn()
        cursor.execute('SELECT email FROM users WHERE linked_cameras LIKE ?', ('%' + camera_mac + '%',))
        rows = cursor.fetchall()
        return len(rows)

    def user_exists(self, email):
        _, cursor = self._get_conn()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        if row:
            return True
        return False