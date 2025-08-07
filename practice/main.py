from tracker_utils import load_tracked_paths, display_tracked_paths
from FileObserver import start_monitoring
from ssh_utils import ssh_sender_worker
import threading
import settings_util
from pathlib import Path


def main():
  settings_util.load_settings()

  inbox_folder = settings_util.settings.get('local_inbox')

  if inbox_folder is None or inbox_folder == "":
    print("\nPlease enter an absolute local path to serve as the inbox folder.")
    print("(All files that are received should land in this folder.)")
    print("** You must put this folder as the inbox folder when tracking files on the remote system as well.")

    inbox_folder = Path(input("\nInbox folder: ").strip())

    # Ensure the path exists
    inbox_folder.mkdir(parents=True, exist_ok=True)

    print(f"Saving to {settings_util.SETTINGS_FILE}")
    settings_util.settings['local_inbox'] = inbox_folder.as_posix()
    settings_util.save_settings()
  else:

    # Ensure the path exists
    inbox_folder = Path(inbox_folder)
    inbox_folder.mkdir(parents=True, exist_ok=True)

  inbox_folder = inbox_folder.as_posix()

  print(f"\nInbox Path: {inbox_folder}")

  display_tracked_paths()
  # Start the SSH sender worker thread
  sender_thread = threading.Thread(target=ssh_sender_worker, daemon=True)
  sender_thread.start()

  tracked_paths = load_tracked_paths()

  start_monitoring(tracked_paths)

if __name__ == "__main__":
  main()