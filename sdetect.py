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
import multiprocessing

logging.basicConfig(filename='error_log.txt', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class ProgressBar:
    def __init__(self, total_interfaces, stdscr):
        self.total_interfaces = total_interfaces
        self.stdscr = stdscr
        self.current_interface = ''
        self.current_progress = 0.0
        self.current_stream_type = ''
        self.current_pid = ''

class PacketAnalyzer:
    def __init__(self, interface, queue):
        self.interface = interface
        self.queue = queue
        self.capture = pyshark.LiveCapture(interface=self.interface)
    
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
            
    async def start(self):
        await self.packet_capture()

    async def packet_capture(self):
        for packet in self.capture.sniff_continuously():
            payload = packet.raw_mode.packet_data
            if self.is_video_stream(payload):
                self.queue.put(f"Detected video stream on {self.interface}")

        
async def packet_capture_process(interface, queue):
    analyzer = PacketAnalyzer(interface, queue)
    await analyzer.start()

def main(stdscr):
    interfaces = netifaces.interfaces()
    total_interfaces = len(interfaces)  # Including 'lo' interfaces
    analyzer_processes = []
    video_streams_queue = multiprocessing.Manager().Queue()  # Use managed queue
    video_streams = []

    progress_bar = ProgressBar(total_interfaces, stdscr)
    progress_thread = threading.Thread(target=progress_bar_update, args=(progress_bar, stdscr, video_streams_queue))
    progress_thread.start()

    for interface in interfaces:
        process = multiprocessing.Process(target=packet_capture_process, args=(interface, video_streams_queue))
        process.start()
        analyzer_processes.append(process)

    try:
        main_curses(stdscr, video_streams_queue, video_streams)
    except KeyboardInterrupt:
        # Clean up processes and threads on keyboard interrupt
        for process in analyzer_processes:
            process.terminate()
            process.join()
            progress_thread.join()

def main_curses(stdscr, video_streams_queue, video_streams):
    curses.curs_set(0)  # Hide cursor
    stdscr.clear()
    stdscr.refresh()

    while True:
        stdscr.clear()

        # Print detected video streams
        row = 2
        for stream in video_streams:
            stdscr.addstr(row, 0, stream)
            row += 1

        stdscr.refresh()
        curses.napms(100)  # Sleep for 100 milliseconds

        # Check for user input (q to quit)
        if stdscr.getch() == ord('q'):
            break


def progress_bar_update(progress_bar, stdscr, video_streams_queue):
    video_streams = []
    while True:
        if not video_streams_queue.empty():
            stream = video_streams_queue.get()
            video_streams.append(stream)
        row = 0
        for stream in video_streams:
            stdscr.addstr(row, 0, stream)
            row += 1
        stdscr.refresh()
        curses.napms(100)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    curses.wrapper(main)
    loop.close()
