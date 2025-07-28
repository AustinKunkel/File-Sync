from pathlib import Path
import file_indexer_hasher
import tracker_utils
import json

def get_user_selected_paths():
  print("Please enter the file paths you want to track.")
  print("Type 'done' when you are finished.\n")

  selected = []

  while True:
    user_input = input("Enter file path (or 'done'): ").strip()
    if user_input.lower() == 'done':
      break
    path = Path(user_input).resolve()
    if path.exists():
      posix_path = path.as_posix()
      selected.append(posix_path)
      print(f"\tAdded: {posix_path}")
    else:
      print("\tThat path doesn't exist. Try again.")

  return selected


def handle_add_paths():
  """Handles adding new paths to the tracked paths."""

  # Get new paths from user
  new_paths = get_user_selected_paths()

  if not new_paths:
    print("No new paths provided. Exiting add operation.")
    return

  # Save the updated list of tracked paths
  tracker_utils.add_tracked_paths(new_paths)

  all_paths = tracker_utils.load_tracked_paths() # loads the folder paths and their metadata

  # now we index and hash the files in the tracked paths
  print("\nIndexing files in the tracked paths...")

  for path, metadata in all_paths.items():
    folder_path = Path(path).resolve()
    if folder_path.is_dir():
      print(f"\tIndexing files in: {folder_path.as_posix()}...", end="    ")

      new_hash = tracker_utils.compute_folder_hash(folder_path)
      stored_hash = metadata.get('hash')

      if(stored_hash == new_hash):
        print("No changes detected, skipping indexing...")
        continue

      # Index the files in the folder
      index = file_indexer_hasher.build_file_index(folder_path)
      file_indexer_hasher.save_index_to_file(index, folder_path.name)
      print(f"File index created with {len(index)} entries.")

      print(f"\nUpdating folder tracking information for {folder_path}...")
      all_paths[path]['hash'] = new_hash
      all_paths[path]['size'] = tracker_utils.get_folder_size(folder_path)
      all_paths[path]['tracked_on'] = tracker_utils.datetime.now().isoformat(timespec='seconds')
      tracker_utils.save_tracked_paths(all_paths)

    else:
      print(f"Skipping {folder_path.as_posix()} as it is not a valid directory.")

    
def handle_remove_paths():
  """Handles removing paths from the tracked paths."""
  paths = tracker_utils.load_tracked_paths()

  tracker_utils.display_tracked_paths()
  print()

  user_input = None
  input_list = []
  while True:
    user_input = input("Enter the numbers of the paths you want to remove, separated by commas (e.g., 1,3,5), or type 'exit': ").strip().lower()
    if not user_input:
      print("No input provided. Please enter valid path numbers.")
      continue
    if user_input == 'exit' or user_input == 'e':
      print("Exiting remove operation.")
      return
    user_input.split(',')
    user_input = [x.strip() for x in user_input.split(',')]
    if all(x.isdigit() and 1 <= int(x) <= len(paths) for x in user_input):
      input_list = [int(x) for x in user_input]
      break
    else:
      print("Invalid input. Please enter valid path numbers.")
      continue

  path_items = list(paths.items())
  removed_paths = []

  # prepare the list to be deleted for confirmation
  files_to_delete = []
  for index in sorted(input_list, reverse=True):
    path, _ = path_items[index - 1]
    files_to_delete.append(path)

  #confirmation prompt
  print("\nWarning! Are you sure you want to delete these files and their indexes?")
  for p in files_to_delete:
    print(f" - {p}")
  confirm = input("\nY/N: ").strip().lower()
  if confirm not in ['y', 'yes']:
    print("Delete operation cancelled.")
    return
  
  #proceed with deletion
  print("\nRemoving paths...")
  for index in sorted(input_list, reverse=True):
    path, _ = path_items[index - 1]
    removed_paths.append(path)
    del paths[path]
    
    # delete the corresponding file index
    folder_name = Path(path).name
    json_filename = file_indexer_hasher.get_index_filename(folder_name)

    if json_filename.exists():
      json_filename.unlink()
      print(f"Removed file index for {path} at {json_filename.as_posix()}")
    else:
      print(f"No file index found for {path} at {json_filename.as_posix()}")

  print(f"Successfully removed {len(removed_paths)} paths: {', '.join(removed_paths)}")
  for p in removed_paths:
    print(f"\t - {p}")

  # save updated tracked paths
  print("\nSaving updated tracked paths...")
  tracker_utils.save_tracked_paths(paths)



if __name__ == "__main__":
  print("Welcome to the File Tracker!")
    
  # Load existing tracked paths
  tracked_paths = tracker_utils.load_tracked_paths()
  
  # Display currently tracked paths
  tracker_utils.display_tracked_paths()
  
  user_choice = None
  # Ask user for action until valid input is received
  while(True):
    user_choice = input("What actions would you like to complete? (add/remove/exit): ").strip().lower()
    if user_choice in ['add', 'a', 'remove', 'r', 'exit', 'e']:
      break
    print("Please answer with 'yes' or 'no'.")

  if user_choice in ['add', 'a']:
    handle_add_paths()
  elif user_choice in ['remove', 'r']:
    handle_remove_paths()
  else:
    print("Exiting the File Tracker. Goodbye!")
    exit(0)