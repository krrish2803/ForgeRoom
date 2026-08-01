import asyncio
from typing import Dict, Any

class StreamContext:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.is_paused = False
        self.redirect_message = ""
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # Default to not paused (set = running)
        self.cancel_event = asyncio.Event()

    def pause(self):
        self.is_paused = True
        self.pause_event.clear()

    def resume(self):
        self.is_paused = False
        self.pause_event.set()

    def redirect(self, new_message: str):
        self.redirect_message = new_message

    def cancel(self):
        self.cancel_event.set()

# Active streams registry: room_id -> StreamContext
active_streams: Dict[str, StreamContext] = {}

def get_stream_context(room_id: str) -> StreamContext:
    if room_id not in active_streams:
        active_streams[room_id] = StreamContext(room_id)
    return active_streams[room_id]

def remove_stream_context(room_id: str):
    if room_id in active_streams:
        del active_streams[room_id]
