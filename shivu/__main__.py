import importlib
import time
import random
import re
import asyncio
from html import escape 
from threading import Thread
from flask import Flask
from shivu import hax
import nest_asyncio
nest_asyncio.apply()
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "Shivu Daemon Running on 7860"

def run_flask():
    flask_app.run(host="0.0.0.0", port=7860, debug=False, use_reloader=False)

        

def main() -> None:
    """Run bot."""

    print("hello")
    
if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    hax.start()
    LOGGER.info("Bot started")
    main()
