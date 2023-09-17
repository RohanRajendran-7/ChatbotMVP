from flask import Flask, request, render_template
import random

app = Flask(__name__)

# Sample responses for the chatbot
responses = [
    "Hello there!",
    "How can I assist you?",
    "Tell me more about your request.",
    "I'm here to help!",
    "Is there anything specific you'd like to know?",
]

def get_bot_response(user_input):
    return random.choice(responses)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_response', methods=['POST'])
def get_response():
    user_input = request.form['user_input']
    bot_response = get_bot_response(user_input)
    return {'bot_response': bot_response}

if __name__ == '__main__':
    app.run(port=8001)
