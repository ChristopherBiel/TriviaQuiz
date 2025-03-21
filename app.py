from backend import app
from backend.db import close_db

@app.teardown_appcontext
def cleanup(error=None):
    close_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5600)
