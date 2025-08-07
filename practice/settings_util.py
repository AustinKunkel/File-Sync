import yaml

SETTINGS_FILE = "./file_indexes/config.yaml"
settings = {}

def load_settings():
  global settings

  with open(SETTINGS_FILE, "r") as f:
    settings = yaml.safe_load(f)


def save_settings():
  global settings

  with open(SETTINGS_FILE, "w") as f:
    yaml.safe_dump(settings, f, indent=2)

def get_settings():
  return settings


  