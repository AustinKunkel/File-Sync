from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
from pathlib import Path
from comparison_logic import compare_folder_hash
from tracker_utils import save_tracked_paths
from file_indexer_hasher import build_file_index, save_index_to_file, get_index_filename, load_index_from_file
from ssh_utils import send_files_over_ssh, add_file_to_queue, parse_remote_path

class ChangeHandler(FileSystemEventHandler):
  def __init__(self, tracked_paths):
    self.tracked_paths = tracked_paths

  def on_modified(self, event):
    path = Path(event.src_path)
    for tracked_path, folder_info in self.tracked_paths.items():
      folder_path = Path(tracked_path)
      # Check if the changed file is inside a tracked folder
      if folder_path in path.parents or folder_path == path:
        print(f"\nChange detected in: {path}")

        # Update the file index only for the changed file
        try:
          stat = path.stat()
          from file_indexer_hasher import generate_file_hash
          file_hash = generate_file_hash(path)
          rel_path = path.relative_to(folder_path).as_posix()
          new_file_info = {
            "hash": file_hash,
            "size": stat.st_size,
            "modified_time": stat.st_mtime
          }

          

          # Queue and send the changed file
          add_file_to_queue(path, folder_info['linked_paths'])
          send_files_over_ssh()

          # Load old index, update only the changed file
          index = load_index_from_file(tracked_path)
          if new_file_info:
            index[rel_path] = new_file_info
          else:
            # Remove deleted file from index
            if rel_path in index:
              del index[rel_path]
          save_index_to_file(index, folder_path.as_posix())


          print(f"Updated index and sent: {path}")

        except Exception as e:
          print(f"Error updating index or sending {path}: {e}")

        break
    save_tracked_paths(self.tracked_paths)

  def on_created(self, event):
    self.on_modified(event)  # You can treat creation same as modification

  def on_deleted(self, event):
    self.on_modified(event)  # You can treat deletion same as modification

def start_monitoring(tracked_paths):
  event_handler = ChangeHandler(tracked_paths)
  observer = Observer()

  for path in tracked_paths:
    observer.schedule(event_handler, path, recursive=True)

  observer.start()
  print("Monitoring started. Press Ctrl+C to stop.")
  try:
    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    observer.stop()
  observer.join()