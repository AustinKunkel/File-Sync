from tracker_utils import load_tracked_paths, display_tracked_paths
from FileObserver import start_monitoring


def main():
  display_tracked_paths()
  tracked_paths = load_tracked_paths()
  start_monitoring(tracked_paths)

if __name__ == "__main__":
  main()