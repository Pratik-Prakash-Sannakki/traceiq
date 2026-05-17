import os
import uvicorn
from dotenv import load_dotenv

def main():
    load_dotenv()
    from traceiq.api.app import create_app
    app = create_app()
    print("TraceIQ running at http://localhost:8000")
    print("Phoenix:  ", os.environ.get("PHOENIX_URL", "http://localhost:6006"))
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
