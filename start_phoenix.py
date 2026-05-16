import phoenix as px
import time

print("Starting Phoenix...")
session = px.launch_app()
print(f"Phoenix URL: {session.url}")
time.sleep(60)
