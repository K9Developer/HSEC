import os
import av
import cv2
import numpy as np
import datetime
import gzip
import io

from package.camera_server.constants import Constants

timelapse_current_chunks = {}  # {id: {time_started: datetime.datetime, frames: list, size, last_added}}
class PlaybackManager:

    @staticmethod
    def save_chunk(camera_id: str):
        if camera_id not in timelapse_current_chunks:
            return

        chunk = timelapse_current_chunks[camera_id]
        frames = chunk["frames"]

        buffer = io.BytesIO()
        with av.open(buffer, 'w', format='mp4') as container:
            stream = container.add_stream('h264', rate=int(Constants.TIMELAPSE_FPS))  # use 5 fps for maximum size reduction
            stream.width = 320   # or chunk["size"][0] if you keep it small from start
            stream.height = 240  # or chunk["size"][1]
            stream.pix_fmt = 'yuv420p'
            stream.options = {"crf": "40", "preset": "veryslow"}
            for frame in frames:
                # Optionally resize here to 320x240:
                if frame.shape[0] != 240 or frame.shape[1] != 320:
                    frame = cv2.resize(frame, (320, 240))
                f = av.VideoFrame.from_ndarray(frame, format='bgr24')
                for packet in stream.encode(f):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        video_bytes = buffer.getvalue()

        chunk_bytes = b""
        chunk_bytes += camera_id.encode() + b"\0" + chunk["time_started"].isoformat().encode() + b"\0" + (320).to_bytes(4, 'big') + b"\0" + (240).to_bytes(4, 'big') + b"\0"
        # compressed_video = gzip.compress(video_bytes, compresslevel=1)  # gzip is not very helpful here; can use lowest level for speed
        chunk_bytes += video_bytes
        chunk_filename = f"recordings/{camera_id}/{chunk['time_started'].strftime('%Y-%m-%d_%H-%M-%S')}.mp4.gz"
        with open(chunk_filename, "wb") as f:
            f.write(chunk_bytes)

    @staticmethod
    def get_recorded_time_range(camera_id: str):
        camera_id = camera_id.replace(":", "-")
        if not os.path.exists(f"recordings/{camera_id}"):
            return None, None

        files = [f for f in os.listdir(f"recordings/{camera_id}") if f.endswith(".mp4.gz")]
        if not files:
            return None, None

        start_time = None
        end_time = None

        for file in files:
            timestamp_str = file.split(".", 1)[0]
            timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
            if start_time is None or timestamp < start_time:
                start_time = timestamp
            if end_time is None or timestamp > end_time:
                end_time = timestamp
        return start_time, end_time

    @staticmethod
    def get_chunk(camera_id: str, time: datetime.datetime):
        camera_id = camera_id.replace(":", "-")
        if not os.path.exists(f"recordings/{camera_id}"):
            return None

        range_start, range_end = PlaybackManager.get_recorded_time_range(camera_id)
        if range_start is None or range_end is None: return None
        if time < range_start or time > range_end: return None

        files = [f for f in os.listdir(f"recordings/{camera_id}") if f.endswith(".mp4.gz")]
        for file in files:
            chunk_start = datetime.datetime.strptime(file.split(".", 1)[0], "%Y-%m-%d_%H-%M-%S")
            if 0 <= (time - chunk_start).total_seconds() < Constants.TIMELAPSE_CHUNK_DURATION:
                with open(f"recordings/{camera_id}/{file}", "rb") as f:
                    chunk_data = f.read()
                camera_id, time_started_str, extra = chunk_data.split(b"\0", maxsplit=2)
                width = extra[:4]
                height = extra[5:9]
                video_data = extra[10:]

                time_started = datetime.datetime.fromisoformat(time_started_str.decode())
                # video_data = gzip.decompress(video_data)
                return {
                    "camera_id": camera_id.decode(),
                    "time_started": time_started,
                    "video_data": video_data,
                    "duration": Constants.TIMELAPSE_CHUNK_DURATION,
                    "size": (int.from_bytes(width, 'big'), int.from_bytes(height, 'big'))
                }

    @staticmethod
    def add_frame(camera_id: str, jpg_frame: bytes):
        camera_id = camera_id.replace(":", "-")
        if camera_id in timelapse_current_chunks and (datetime.datetime.now() - timelapse_current_chunks[camera_id]["last_added"]).total_seconds() < Constants.TIMELAPSE_FPS:
            return

        if not os.path.exists(f"recordings/{camera_id}"):
            os.makedirs(f"recordings/{camera_id}")

        cv2_frame = cv2.imdecode(np.frombuffer(jpg_frame, np.uint8), cv2.IMREAD_COLOR)

        if camera_id not in timelapse_current_chunks:
            frame_height, frame_width = cv2_frame.shape[:2]
            timelapse_current_chunks[camera_id] = {
                "time_started": datetime.datetime.now(),
                "frames": [],
                "size": (frame_width, frame_height),
                "last_added": datetime.datetime.now()
            }

        timelapse_current_chunks[camera_id]["frames"].append(cv2_frame)
        elapsed_time = len(timelapse_current_chunks[camera_id]["frames"]) / Constants.TIMELAPSE_FPS
        if elapsed_time >= Constants.TIMELAPSE_CHUNK_DURATION:
            PlaybackManager.save_chunk(camera_id)
            if camera_id in timelapse_current_chunks: del timelapse_current_chunks[camera_id]

    @staticmethod
    def get_chunks_merged(camera_id: str, start_time: datetime.datetime, chunks: int):
        if not os.path.exists(f"recordings/{camera_id}"):
            return None

        chunk_list = []
        for i in range(chunks):
            chunk = PlaybackManager.get_chunk(camera_id, start_time + datetime.timedelta(seconds=i * Constants.TIMELAPSE_CHUNK_DURATION))
            if chunk is None:
                break
            chunk_list.append(chunk)

        if not chunk_list:
            return None

        big_chunk = {
            "camera_id": camera_id,
            "time_started": chunk_list[0]["time_started"],
            "video_data": b"",
            "duration": len(chunk_list) * Constants.TIMELAPSE_CHUNK_DURATION,
            "size": chunk_list[0]["size"]
        }

        first_chunk = chunk_list[0]
        frames = []
        for chunk in chunk_list:
            with av.open(io.BytesIO(chunk["video_data"]), 'r') as container:
                for frame in container.decode(video=0):
                    arr = frame.to_ndarray(format='bgr24')
                    frames.append(arr)
        buffer = io.BytesIO()
        with av.open(buffer, 'w', format='mp4') as container:
            stream = container.add_stream('h264', rate=int(Constants.TIMELAPSE_FPS))
            stream.width = first_chunk["size"][0]
            stream.height = first_chunk["size"][1]
            stream.pix_fmt = 'yuv420p'
            stream.options = {"crf": "38", "preset": "veryslow"}
            for frame in frames:
                f = av.VideoFrame.from_ndarray(frame, format='bgr24')
                for packet in stream.encode(f):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        big_chunk["video_data"] = buffer.getvalue()
        return big_chunk
