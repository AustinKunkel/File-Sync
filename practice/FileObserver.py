from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileMovedEvent
import time
from pathlib import Path
from comparison_logic import compare_folder_hash
from tracker_utils import save_tracked_paths
from file_indexer_hasher import save_index_to_file, load_index_from_file, generate_file_hash
from ssh_utils import file_event_queue
import traceback
from FileActions import FileAction
import settings_util
import shutil

# Time to wait to verify file is stable (not being written anymore)
STABLE_WAIT = 1.0

file_skip_dict = dict() # dictionary of files for the observer to skip (must be skipped when receiving) [filepath] -> timestamp

class ChangeHandler(FileSystemEventHandler):
  def __init__(self, tracked_paths):
    self.tracked_paths = tracked_paths
    self.inbox_path = Path(settings_util.settings['local_inbox']).resolve()

  def on_modified(self, event):

    # If the file is in the inbox folder
    if event.src_path.startswith(str(self.inbox_path)):
      absolute_path = Path(event.src_path)
      try:
        relative_path = absolute_path.relative_to(self.inbox_path)
      except ValueError:
        relative_path = absolute_path

      file_skip_dict[relative_path] = time.time() # make sure the file gets skipped when the system picks up whatever change it gets
      self.handle_on_inbox(absolute_path, FileAction.SEND_FILE)
      return
    
    path = Path(event.src_path)

    # If the file was moved from the inbox folder, check how long ago 
    if path in file_skip_dict.keys():
      current_time = time.time()
      old_time = file_skip_dict[path]

    
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
    save_tracked_paths(self.tracked_paths)

  def on_created(self, event):
    self.on_modified(event)  # You can treat creation same as modification

  def on_deleted(self, event):
    self.on_modified(event)  # You can treat deletion same as modification

  def on_moved(self, event):
    if isinstance(event, FileMovedEvent):
      pass

  def handle_on_inbox(self, src_path, action : FileAction):

    if action == FileAction.SEND_FILE:
      # ensure the path is inside the inbox
      try:
        rel_path = src_path.relative_to(settings_util.settings['local_inbox'])
      except ValueError:
        print(f"Path {src_path} is not inside the inbox base.")
        return
      
      dest_path = Path("/") / rel_path
      # Ensure destination directory exists
      dest_path.parent.mkdir(parents=True, exist_ok=False)

      try:
        shutil.move(str(src_path), str(dest_path))
        print(f"Moved {src_path} -> {dest_path}")
      except Exception as e:
        print(f"Failed to move file: {e}")
        traceback.print_exc(e)

def start_monitoring(tracked_paths):
  event_handler = ChangeHandler(tracked_paths)
  observer = Observer()

  for path in tracked_paths:
    observer.schedule(event_handler, path, recursive=True)

  inbox_path = settings_util.settings['local_inbox']
  observer.schedule(event_handler, inbox_path, recursive=True)

  observer.start()
  print("Monitoring started. Press Ctrl+C to stop.")
  try:
    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    observer.stop()
  observer.join()