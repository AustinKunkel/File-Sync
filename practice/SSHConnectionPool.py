import time
import paramiko
import threading

class SSHConnectionPool:
  def __init__(self, timeout=180, max_connections=10):
    self.timeout = timeout
    self.max_connections = max_connections
    self.connections = {}
    self.lock = threading.RLock() # Use RLock to allow re-entrant locking

  def get_connection(self, user, host, ssh_key_path):
    with self.lock:
      # print("Acquiring SSH connection...")
      now = time.time()
      # print(f"Current time: {now}")
      # print("Cleaning up old connections...")
      self.cleanup(now)
      # print("Cleaned up old connections.")


      key = (user, host)
      try:

        if key in self.connections:
          ssh, _ = self.connections[key]
          if ssh.get_transport() is None or not ssh.get_transport().is_active():
            print(f"Transport dead for {user}@{host}, reconnecting...")
            ssh.close()
            del self.connections[key]  # Remove stale connection
          else:
            self.connections[key] = (ssh, now)
            print(f"Reusing existing connection to {host} as {user}.")
            return ssh
        else:
          ssh = paramiko.SSHClient()
          ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
          print(f"Connecting to {host} as {user}...")
          ssh.connect(
            hostname=host,
            username=user,
            key_filename=ssh_key_path
          )
          transport = ssh.get_transport()
          if not transport or not transport.is_active():
              raise Exception("SSH connection failed (transport is not active)")
          transport.set_keepalive(30)
          self.connections[key] = (ssh, now)
          return ssh
      except Exception as e:
        print(f"Failed to connect to {host} as {user}: {e}")
        return None
      
  def cleanup(self, now=None):
    if now is None:
      now = time.time()
    to_close = []
    with self.lock:
      # Close connections that have been idle for longer than the timeout
      for key, (ssh, last_used) in list(self.connections.items()):
        if now - last_used > self.timeout:
          ssh.close()
          to_close.append(key)
      for key in to_close:
        del self.connections[key]

  def close_all(self):
    with self.lock:
      # Close all connections
      for ssh, _ in self.connections.values():
        ssh.close()
      self.connections.clear()
