import threading
import psutil
import pyshark
import netifaces
import asyncio
import curses
import queue
import time
import os
import logging

# Configure the logging module
logging.basicConfig(filename='error_log.txt', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class PacketAnalyzer:
    def __init__(self, interface, queue, loop):
        self.interface = interface
        self.queue = queue
        self.capture = pyshark.LiveCapture(interface=self.interface)
        self.loop = loop  # Pass the existing event loop

   def is_video_stream(self, payload):
        # Traditional Video Patterns
        video_patterns = [
            b'\x00\x00\x00\x01',  # MPEG-4 Visual / H.264 / HEVC video formats
            b'\x00\x00\x01\xB3',  # Motion JPEG 2000 video format
            b'\x9D\x01\x2A\xDF',  # AVCHD / AVCHD Lite video format
            b'\x30\x2A\xD7\x30',  # H.263 video format
        ]

        # Unorthodox Video Patterns
        unorthodox_video_methods = [
            b'\xFF\xD8',           # Start of JPEG image
            b'\x89\x50\x4E\x47',   # Start of PNG image
            b'BM',                 # Start of BMP image
            b'\x1A\x45\xDF\xA3',   # Start of WebM video
            b'FLV',                # Start of Flash Video (FLV) file
            b'GIF87a',             # Start of GIF 87a image
            b'GIF89a',             # Start of GIF 89a image
            b'\x00\x00\x00\x18',   # Start of 3GPP media file
            # AVI video format
            b'RIFF....AVI LIST',
            # MOV video format
            b'moov....mdat',
        ]

        for method in unorthodox_video_methods:
            if method in payload:
                return True

        return False

    async def _packet_capture(self):
        for packet in self.capture.sniff_continuously():
            payload = packet.raw_mode.packet_data
            if self._is_video_stream(payload):
                self.queue.put(f"Detected video stream on {self.interface}")

    def start(self):
 def start(self):
        asyncio.set_event_loop(self.loop)  # Use the existing loop
        asyncio.ensure_future(self._packet_capture())  # Schedule the coroutine
        self.loop.run_forever()  # Run the loop indefinitely
# ... (rest of the ProgressBar class)

def main(stdscr):
    interfaces = netifaces.interfaces()
    total_interfaces = len(interfaces)  # Including 'lo' interfaces
    analyzer_threads = []
    streams_queue = queue.Queue()
    video_streams = []

    loop = asyncio.get_event_loop()
    progress_bar = ProgressBar(total_interfaces, stdscr)
    progress_thread = threading.Thread(target=progress_bar_update, args=(progress_bar, stdscr))  # Pass stdscr here
    progress_thread.start()

    for interface in interfaces:
        analyzer = PacketAnalyzer(interface, streams_queue, loop)
        thread = threading.Thread(target=analyzer.start)
        thread.start()
        analyzer_threads.append(thread)

    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass

def progress_bar_update(progress_bar, stdscr):
    while True:
        if not streams_queue.empty():
            stream = streams_queue.get()
            video_streams.append(stream)
        row = 0
        for stream in video_streams:
            stdscr.addstr(row, 0, stream)
            row += 1
        stdscr.refresh()
        curses.napms(100)  # Sleep for 100 milliseconds
        progress_bar.update()

if __name__ == "__main__":
    curses.wrapper(main)
