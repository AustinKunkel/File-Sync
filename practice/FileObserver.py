from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
from pathlib import Path

class ChangeHandler(FileSystemEventHandler):
  def __init__(self, tracked_paths):
    self.tracked_paths = set(Path(p) for p in tracked_paths)

  def on_modified(self, event):
    path = Path(event.src_path)
    for tracked_path in self.tracked_paths:
      if tracked_path in path.parents or tracked_path == path:
        print(f"Change detected in: {path}")
        break

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