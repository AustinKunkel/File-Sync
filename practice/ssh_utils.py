import paramiko
from pathlib import Path
import os
import traceback
from SSHConnectionPool import SSHConnectionPool
import queue
from FileActions import FileAction

ssh_pool = SSHConnectionPool(timeout=180)
file_event_queue = queue.Queue()

file_send_queue = dict()
file_rename_queue = dict()
file_delete_queue = dict()

def send_files_over_ssh():
  global file_send_queue
  """Sends the files in the queue to the remote host using SSH."""
  ssh_key_path = Path.home() / ".ssh" / "id_ed25519"
  failed_queue = {}

  # Group files by SSH destination
  ssh_groups = group_files_by_ssh(file_send_queue)

  # For each SSH Group, open a connection and send files
  for (user, host), file_list in ssh_groups.items():
    # print(f"Connecting to {host} as {user}...")

    ssh = ssh_pool.get_connection(user, host, ssh_key_path.as_posix())
    if ssh is None or ssh.get_transport() is None or not ssh.get_transport().is_active():
      print("Connection is unusable. Skipping.")
    if ssh is None:
      print(f"Could not establish SSH connection to {host} as {user}. Skipping this group.")
      for file, remote_path, _, _ in file_list:
          failed_queue.setdefault(file, []).append(remote_path)
      continue  # Skip to next group

    print("Connected. Sending files...")

    try:
      sftp = ssh.open_sftp()
      for file, remote_path, tracked_path, inbox_path in file_list:
        path = Path(file)
        folder_path = Path(tracked_path)
        try:
          if path.is_file():
            relative = path.relative_to(folder_path)
            remote_file_path = f"{inbox_path}/{remote_path.lstrip('/')}/{relative.as_posix()}"
            remote_subdir = os.path.dirname(remote_file_path)
            ensure_remote_dir(sftp, remote_subdir)
            print(remote_file_path)
            send_file(sftp, str(path), str(remote_file_path))
          elif path.is_dir():
            for subpath in path.rglob('*'):
              if subpath.is_file():
                relative = subpath.relative_to(path)
                remote_file_path = f"{inbox_path}/{remote_path.lstrip('/')}/{relative.as_posix()}"
                remote_subdir = os.path.dirname(remote_file_path)
                ensure_remote_dir(sftp, remote_subdir)
                send_file(sftp, str(subpath), str(remote_file_path))
        except Exception as e:
          print(f"Failed to send {file} to {remote_path}: {e}")
          traceback.print_exc()
          failed_queue.setdefault(file, []).append(remote_path)
      sftp.close()
    except Exception as e:
      print(f"Failed to connect to {host} as {user}: {e}")
      traceback.print_exc()
      # Mark all files for this host/user as failed
      for file, remote_path, _, _ in file_list:
        failed_queue.setdefault(file, []).append(remote_path)

  print("Files sent. Failed transfers:", failed_queue)
  return failed_queue

def rename_files_over_ssh():
  global file_rename_queue
  """Renames a file remotely using the queue"""

  ssh_key_path = Path.home() / ".ssh" / "id_ed25519"
  failed_queue = {}

  # Group files by SSH destination
  ssh_groups = group_files_by_ssh(file_rename_queue, extra_keys=["old_path"])

  # For each SSH Group, open a connection and send files
  for (user, host), file_list in ssh_groups.items():
    # print(f"Connecting to {host} as {user}...")

    ssh = ssh_pool.get_connection(user, host, ssh_key_path.as_posix())
    if ssh is None or ssh.get_transport() is None or not ssh.get_transport().is_active():
      print("Connection is unusable. Skipping.")
    if ssh is None:
      print(f"Could not establish SSH connection to {host} as {user}. Skipping this group.")
      for file, remote_path, _, _ in file_list:
          failed_queue.setdefault(file, []).append(remote_path)
      continue  # Skip to next group

    print("Connected. Renaming files...")

  try:
    sftp = ssh.open_sftp()
    for file, remote_path, tracked_path, old_path in file_list:
      new_path = Path(file)
      old_path = Path(old_path)
      folder_path = Path(tracked_path)
      try:
        if new_path.is_file():
          relative = new_path.relative_to()
      except Exception as e:
        print(f"Error occurred: {e}")

  except Exception as e:
    print(f"Error occurred: {e}")


def group_files_by_ssh(file_queue : dict, extra_keys : list = []) -> dict:
  """
  Groups the files by their remote directory.

  The keys of the output dictionary are the remote directories ([remote] -> local)
  """
  ssh_groups = {}
  for file, info in file_queue.items():
    remote_dirs = info["remote_dirs"] # dictionary of [full_remote_path] -> [remote_path_info]
    tracked_path = info["tracked_path"]

    extra_values = tuple(info.get(k) for k in extra_keys)

    for _, remote_info in remote_dirs.items():
      user = remote_info["user"]
      host_url = remote_info["host_url"]
      base_path = remote_info["base_path"]
      remote_path = remote_info["remote_path"]
      inbox_path = remote_info["inbox_path"]

      remote_path = f"{base_path}/{remote_path}"

      group_key = (user, host_url)
      if group_key not in ssh_groups:
        ssh_groups[group_key] = []
      ssh_groups[group_key].append((file, remote_path, tracked_path, inbox_path, *extra_values))

  return ssh_groups


def ssh_sender_worker():
  global file_event_queue
  """Worker thread to send files over SSH."""
  while True:
    try:
      path, linked_paths, tracked_path, action, old_path = file_event_queue.get(timeout=1)
      print(f"Dequeued for sending: {path} -> {', '.join(linked_paths.keys())} (tracked: {tracked_path}), action: {action}")
      add_file_to_queue(path, linked_paths, tracked_path, action, old_path)
      send_files_over_ssh()
    except queue.Empty:
      continue  # No file to send, keep waiting
  

def send_file(sftp : paramiko.SFTPClient, local_file : Path, remote_file : str):
  print(f"Sending {local_file} to {remote_file}...")
  sftp.put(str(local_file), remote_file)

def rename_file(sftp : paramiko.SFTPClient, remote_old : str, remote_new : str):
  print(f"Renaming file {remote_old} to match {remote_new}")
  sftp.rename(remote_old, remote_new)

def ensure_remote_dir(sftp : paramiko.SFTPClient, remote_path):
  """Creates the remote directory if it does not exist."""
  try:
    sftp.stat(remote_path)
  except FileNotFoundError:
    parent = os.path.dirname(remote_path)
    if parent and parent != remote_path:
      ensure_remote_dir(sftp, parent)
    try:
      sftp.mkdir(remote_path)
      print(f"Created remote directory: {remote_path}")
    except IOError:
      pass  # Already exists (race condition or parallel ops)

def add_file_to_queue(file : str, remote_dirs : dict, tracked_path: str, action: FileAction = FileAction.SEND_FILE, old_path = None):
  global file_send_queue, file_delete_queue, file_rename_queue
  """Adds a file or directory to the correct queue for sending."""
  path = Path(file).resolve()
  if not path.exists():
    print(f"File or directory {file} does not exist. Skipping...")
    return
  
  match action:
    case FileAction.SEND_FILE:
      file_send_queue[path.as_posix()] = {
          "remote_dirs": remote_dirs,
          "tracked_path": tracked_path
        }
    case FileAction.RENAME_FILE:
      if old_path is None:
        print("No old filepath is specified!")
        return
      file_rename_queue[path.as_posix()] = {
          "remote_dirs": remote_dirs,
          "tracked_path": tracked_path,
          "old_path": old_path
        }
    case FileAction.DELETE_FILE:
      file_delete_queue[path.as_posix()] = {
          "remote_dirs": remote_dirs,
          "tracked_path": tracked_path
        }

  print_files_in_queue()

def parse_remote_path(remote_path: str) -> tuple:
  """Parses a remote path into host, username, and directory."""
  if "@" in remote_path:
    user_host, remote_dir = remote_path.split(":", 1)
    user, host = user_host.split("@", 1)
  else:
    host, remote_dir = remote_path.split(":", 1)
    user = None

  # Normalize ~ to /
  if remote_dir.startswith("~"):
    remote_dir = remote_dir[1:]
    if not remote_dir.startswith("./"):
      remote_dir = "./" + remote_dir

  return user, host, remote_dir


def print_files_in_queue():
  global file_send_queue
  """Prints the files currently in the queue."""
  print("\nFiles in the queue:")
  for file, info in file_send_queue.items():
    print(f"\n{file}")
    print(f"\tTracked Path: {info['tracked_path']}")
    print("\tRemote Directories:")
    for remote_dir in info["remote_dirs"]:
      print(f"\t - {remote_dir}")

  

if __name__ == "__main__":
  host = input("Enter the remote host (e.g., hostname): ").strip()
  username = input("Enter the username for the remote host: ").strip()
  local_files_input = input("Enter the local file paths to send (comma-separated): ").strip()
  remote_dir = input("Enter the remote directory to send files to: ").strip()

  local_files = local_files_input.split(',')
  local_files = [file.strip() for file in local_files if file.strip()]

  for file in local_files:
    add_file_to_queue(file,[remote_dir])

  if not local_files:
    print("No valid files provided. Exiting.")
  else:
    send_files_over_ssh()

