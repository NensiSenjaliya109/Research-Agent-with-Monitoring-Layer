import os
import sys
import uvicorn

# Add the project root (two levels up from this file) to sys.path
# so that python can find the 'app' module.
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if __name__ == "__main__":
    # Change current working directory to the project root
    # so that paths like './chroma_db' or './logs' point to the root folder.
    os.chdir(project_root)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)