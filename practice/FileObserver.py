from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileMovedEvent
import time
from pathlib import Path
from tracker_utils import save_tracked_paths
from ssh_utils import file_event_queue
import traceback
from FileActions import FileAction
import settings_util
import shutil
import threading
from queue import Queue, Empty

# Time to wait to verify file is stable (not being written anymore)
STABLE_WAIT = 1

inbox_queue = Queue()
file_skip_dict = dict() # dictionary of files for the observer to skip (must be skipped when receiving) [filepath] -> timestamp
TIME_TO_HANDLE_FILE = 2 # seconds it takes from last change to handle a file if it is inside of the skip dictionary

class ChangeHandler(FileSystemEventHandler):
  def __init__(self, tracked_paths):
    self.tracked_paths = tracked_paths
    self.inbox_path = Path(settings_util.settings['local_inbox']).resolve()

  def on_modified(self, event):

    # If the file is in the inbox folder
    if event.src_path.startswith(str(self.inbox_path)):
      absolute_path = Path(event.src_path)
      inbox_queue.put((absolute_path, time.time(), FileAction.SEND_FILE)) # make sure the file gets handled by the inbox checker
      return
    
    path = Path(event.src_path)
    
    # If the file was moved from the inbox folder, check how long ago 
    if path in file_skip_dict.keys():
      current_time = time.time()
      old_time = file_skip_dict[path] # last update time
      if current_time - old_time >= 2:
        # Enough time has passed where we can send the file to remote
        del file_skip_dict[path]
      else:
        return # dont handle the file

    for tracked_path, folder_info in self.tracked_paths.items():
      folder_path = Path(tracked_path)
      # Check if the changed file is inside a tracked folder
      if folder_path in path.parents or folder_path == path:
        print(f"\nChange detected in: {path}")

        try:
          # Queue and send the changed file
          file_event_queue.put((path, folder_info['linked_paths'], tracked_path, FileAction.SEND_FILE, None))
          print(f"Sent {path} for updating")
        except Exception as e:
          print(f"Error sending {path}: {e}")
          traceback.print_exc()
          
        break

  def on_created(self, event):
    self.on_modified(event)  # You can treat creation same as modification

  def on_deleted(self, event):
    self.on_modified(event)  # You can treat deletion same as modification

  def on_moved(self, event):
    if isinstance(event, FileMovedEvent):
      pass

threading_stop_event = threading.Event()

def check_inbox_worker(tracked_paths):
  """Checks the file skip dictionary to see if there are any files in the inbox. If so, then handle them"""
  while not threading_stop_event.is_set():
    try:
      src_path, last_update_time, action = inbox_queue.get(timeout=1)

      # Ensures enough time has passed to handle the file
      current_time = time.time()
      if current_time - last_update_time <= STABLE_WAIT:
        return
      
      if action == FileAction.SEND_FILE:
        # ensure the path is inside the inbox
        try:
          rel_path = src_path.relative_to(settings_util.settings['local_inbox'])
        except ValueError:
          print(f"Path {src_path} is not inside the inbox base.")
          return
        
        dest_path = Path("/") / rel_path
        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
          file_skip_dict[rel_path] = current_time
          shutil.move(str(src_path), str(dest_path))
          print(f"Moved {src_path} -> {dest_path}")
        except Exception as e:
          print(f"Failed to move file: {e}")
          traceback.print_exc(e)
    except Empty:
      continue
    threading_stop_event.set()
    save_tracked_paths(tracked_paths)
    time.sleep(.1)

def start_monitoring(tracked_paths):
  event_handler = ChangeHandler(tracked_paths)
  observer = Observer()

  for path in tracked_paths:
    observer.schedule(event_handler, path, recursive=True)

  inbox_path = settings_util.settings['local_inbox']
  observer.schedule(event_handler, inbox_path, recursive=True)

  check_inbox_thread = threading.Thread(target=check_inbox_worker, args=(tracked_paths),daemon=True)
  check_inbox_thread.start()

  observer.start()

  print("Monitoring started. Press Ctrl+C to stop.")
  try:
    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    observer.stop()
  print("Cleaning up...")
  threading_stop_event.set()
  check_inbox_thread.join()
  observer.join()