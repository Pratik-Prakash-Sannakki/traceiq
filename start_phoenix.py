import phoenix as px
import time

print("Starting Phoenix...", flush=True)
session = px.launch_app()
print(f"Phoenix running at: {session.url}", flush=True)
while True:
    time.sleep(60)
