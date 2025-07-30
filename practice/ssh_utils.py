import paramiko
from pathlib import Path
import os
import traceback

file_queue = dict()

def send_files_over_ssh():
  global file_queue
  """Sends the files in the queue to the remote host using SSH."""
  ssh_key_path = Path.home() / ".ssh" / "id_ed25519"
  failed_queue = {}

  # Group files by SSH destination
  ssh_groups = {}
  for file, remote_dirs in file_queue.items():
    for remote_dir in remote_dirs:
      user, host, remote_path = parse_remote_path(remote_dir)
      key = (user, host)
      if key not in ssh_groups:
        ssh_groups[key] = []
      ssh_groups[key].append((file, remote_path))

  # For each SSH Group, open a connection and send files
  for (user, host), file_list in ssh_groups.items():
    print(f"Connecting to {host} as {user}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_key_path = Path.home() / ".ssh" / "id_ed25519"
    try:
      ssh.connect(
        hostname=host, 
        username=user, 
        key_filename=ssh_key_path.as_posix()
        )
      sftp = ssh.open_sftp()
      for file, remote_path in file_list:
        path = Path(file)
        try:
          if path.is_file():
            remote_file_path = f"{remote_path}/{path.name}"
            remote_subdir = os.path.dirname(remote_file_path)
            ensure_remote_dir(sftp, remote_subdir)
            print(remote_file_path)
            send_file(sftp, str(path), str(remote_file_path))
          elif path.is_dir():
            for subpath in path.rglob('*'):
              if subpath.is_file():
                relative = subpath.relative_to(path)
                remote_file_path = f"{remote_path}/{path.name}/{relative.as_posix()}"
                remote_subdir = os.path.dirname(remote_file_path)
                ensure_remote_dir(sftp, remote_subdir)
                send_file(sftp, str(subpath), str(remote_file_path))
        except Exception as e:
          print(f"Failed to send {file} to {remote_path}: {e}")
          traceback.print_exc()
          failed_queue.setdefault(file, []).append(remote_path)
      sftp.close()
      ssh.close()
    except Exception as e:
      print(f"Failed to connect to {host} as {user}: {e}")
      # Mark all files for this host/user as failed
      for file, remote_path in file_list:
        failed_queue.setdefault(file, []).append(remote_path)

  print("Files sent. Failed transfers:", failed_queue)
  return failed_queue
  

def send_file(sftp : paramiko.SFTPClient, local_file : Path, remote_file : str):
  # print(f"Sending {local_file} to {remote_file}...")
  sftp.put(str(local_file), remote_file)

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

def add_file_to_queue(file : str, remote_dirs : list):
  global file_queue
  """Adds a file or directory to the queue for sending."""
  path = Path(file).resolve()
  if not path.exists():
    print(f"File or directory {file} does not exist. Skipping...")
    return
  file_queue[path.as_posix()] = remote_dirs

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

