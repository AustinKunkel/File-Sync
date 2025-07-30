import hashlib
from pathlib import Path
import json
from datetime import datetime

TRACKED_PATHS_FILE = Path("file_indexes/tracked_paths.json")

def compute_folder_hash(folder: Path) -> str:
    hasher = hashlib.sha256()
    for file in sorted(folder.rglob("*")):
        if file.is_file():
            stat = file.stat()
            hasher.update(str(file.relative_to(folder)).encode())
            hasher.update(str(stat.st_mtime).encode())
            hasher.update(str(stat.st_size).encode())
    return hasher.hexdigest()

def get_folder_size(folder: Path) -> int:
    return sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())

def save_tracked_paths(paths : dict):
  """Saves the list of tracked paths to a JSON file."""
  TRACKED_PATHS_FILE.parent.mkdir(exist_ok=True)
  with open(TRACKED_PATHS_FILE, 'w') as f:
    json.dump(paths, f, indent=2)
  print(f"Successfully saved {len(paths)} paths to {TRACKED_PATHS_FILE}...")

def load_tracked_paths() -> dict:
  """Loads the list of tracked paths from a JSON file."""
  try:
    with open(TRACKED_PATHS_FILE, 'r') as f:
      return json.load(f)
  except FileNotFoundError:
    print(f"No tracked paths found at {TRACKED_PATHS_FILE}. Starting fresh.")
    return {}
  
def display_tracked_paths():
  """Displays the currently tracked paths loaded."""

  paths = load_tracked_paths()
  if not paths:
    print("No tracked paths found.")
  else:
    print("\nTracked Paths:")
    for i, (path, info) in enumerate(paths.items(), 1):
      print(f"\t{i}. {path}")
      print(f"\t   Size: {info['size']} bytes")
      print(f"\t   Tracked On: {info['tracked_on']}")
      print(f"\t   Hash: {info['hash']}\n")

def add_tracked_paths(new_paths: dict):
  # if not path.exists() or not path.is_dir():
  #   print("Error: Path must exist and be a directory.")
  #   return

  paths = load_tracked_paths()

  for path, linked_paths in new_paths.items():
    path = Path(path).resolve()
    if not path.exists() or not path.is_dir():
      print(f"Error: {path} must exist and be a directory.")
      continue

    posix_path = path.as_posix()
    if posix_path not in paths:
            # Only add empty metadata here; metadata will be set after indexing
            paths[posix_path] = {}
            paths[posix_path]['linked_paths'] = linked_paths

  save_tracked_paths(paths)