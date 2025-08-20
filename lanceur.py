import subprocess
import time

print("Démarrage de l'agent")
time.sleep(5)
subprocess.Popen(["python", "app.py"])

print("All is Running")
