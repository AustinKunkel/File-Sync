from pathlib import Path
import hashlib
import os
import json
from datetime import datetime
import re

def generate_file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def build_file_index(folder_path):
    """Builds an index of files in the specified folder, including their hashes, sizes, and modification times."""
    index = {}
    folder_path = Path(folder_path).resolve()
    
    for filepath in folder_path.rglob("*"):
        if filepath.is_file():
            try:
                stat = filepath.stat()
                file_hash = generate_file_hash(filepath)
                relative_path = filepath.relative_to(folder_path).as_posix()
                index[relative_path] = {
                    "hash": file_hash,
                    "size": stat.st_size,
                    "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            except (OSError, FileNotFoundError) as e:
                print(f"Error processing file {filepath}: {e}")
    
    return index

def get_index_filename(folder_name: str) -> Path:
    output_dir = Path("file_indexes")
    output_dir.mkdir(exist_ok=True)

    sanitized_name = re.sub(r'[^\w\-_.]', '_', folder_name)
    return output_dir / f"{sanitized_name}_file_index.json"

def save_index_to_file(index, folder_name):
    output_file = get_index_filename(folder_name)
    
    with open(output_file, "w") as f:
        json.dump(index, f, indent=2)

if __name__ == "__main__":
    base_folder_path = input("Enter the folder path to index: ").strip()
    folder_path = Path(base_folder_path).resolve()
    
    if not folder_path.is_dir():
        print("Invalid folder path.")
    else:
        index = build_file_index(folder_path)
        save_index_to_file(index, folder_path.name)
        print(f"File index created with {len(index)} entries.")