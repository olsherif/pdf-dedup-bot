from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "OK", 200

def run_web():
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

def start_web_server():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()
