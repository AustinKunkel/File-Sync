import os
import subprocess
from pathlib import Path

def generate_ssh_key(key_type="ed25519"):
  ssh_dir = Path.home() / ".ssh"
  key_file = ssh_dir / f"id_{key_type}"

  if key_file.exists():
    print(f"SSH key already exists at {key_file}.")
    return key_file
  
  ssh_dir.mkdir(parents=True, exist_ok=True)
  print(f"Generating SSH key at {key_file}...")
  subprocess.run(["ssh-keygen", "-t", key_type, "-f", str(key_file), "-N", ""], check=True)
  print(f"SSH key generated successfully at {key_file}.")
  return key_file

def copy_public_key_to_remote(host : str, user : str, key_file : Path):
  public_key_file = key_file.with_suffix(".pub")
  if not public_key_file.exists():
    print(f"Public key file {public_key_file} does not exist. Please generate the SSH key first.")
    return
  
  print(f"Copying public key to {host}...")

  with open(public_key_file, "r") as f:
    public_key = f.read().strip()

  remote_command = (        
    f'mkdir -p ~/.ssh && chmod 700 ~/.ssh && '
    f'echo "{public_key}" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
  )

  try:
    subprocess.run(
      ["ssh", f"{user}@{host}", remote_command],
      check=True
    )
    print(f"Public key copied to {host} successfully.")
  except subprocess.CalledProcessError as e:
    print(f"Failed to copy public key to {host}: {e}")
    return
  
def main():
  print("SSH Key Setup Utility\n")
  key_type = input("Enter SSH key type (ed25519/rsa, default is ed25519): ").strip() or "ed25519"

  host = input("Enter the remote host (e.g., user@hostname): ").strip()
  user = input("Enter the username for the remote host: ").strip()

  try:
    key_file = generate_ssh_key(key_type)
    copy_public_key_to_remote(host, user, key_file)
  except Exception as e:
    print(f"An error occurred: {e}")
    return
  
if __name__ == "__main__":
  main()