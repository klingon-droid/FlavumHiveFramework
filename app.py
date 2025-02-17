from flask import Flask, jsonify
from main import main

app = Flask(__name__)

@app.route('/')
def start_bot():
    main()
    return "FlavumHive-AI-Bot is running!"

if __name__ == '__main__':
    app.run(host='localhost', port=8080)
