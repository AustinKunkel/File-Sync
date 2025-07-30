from tracker_utils import compute_folder_hash
from pathlib import Path
from file_indexer_hasher import generate_file_hash


def compare_folder_hash(folder : Path, old_hash: str = None) -> tuple:
  new_hash = compute_folder_hash(folder)
  return old_hash != new_hash, new_hash

def compare_file_hash(file_path: Path, old_hash: str = None) -> tuple:
  new_hash = generate_file_hash(file_path)
  return old_hash != new_hash, new_hash
