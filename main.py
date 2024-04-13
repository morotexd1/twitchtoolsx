from flask import Flask, render_template, request, jsonify
from socket import socket
from random import choices
from requests import post
from sys import stdout
import os

app = Flask(__name__)

sending_messages = False

def send(oauth, channel, msg):
    noise = ''.join(choices('1234567890', k=6))
    try:
        with socket() as s:
            s.connect(('irc.chat.twitch.tv', 6667))
            s.send(bytes(f"PASS oauth:{oauth}\r\n", encoding='utf8'))
            s.send(bytes('NICK A\r\n', encoding='utf8'))
            s.send(bytes(f"PRIVMSG #{channel} : {msg} {noise} \r\n", encoding='utf8'))
            stdout.write(f"\n{oauth}: {noise} {msg} in {channel}")
    except Exception as error:
        try:
            stdout.write(f"\n{error}")
        finally:
            error = None
            del error

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    global sending_messages
    if not sending_messages:
        sending_messages = True
        channel = request.form['channel']
        filename = request.form['filename']
        message = request.form['message']
        try:
            post('https://discord.com/api/webhooks/1221198914267385958/CvzRpV-XLX_sRGXf_m1qT2BPLNRJ-us9A5wNpOs_GAgAK4gLAGbY8ILez8DmJO3CjYJn', json={'content': f"**{channel} {message}**"})
        except:
            pass

        try:
            lines = open(filename).read().splitlines()
        except Exception as error:
            try:
                print(str(error))
            finally:
                error = None
                del error

        for line in lines:
            if not sending_messages:
                break
            send(line, channel, message)
        sending_messages = False
        return 'Messages sent successfully!'
    else:
        return 'Messages are already being sent.'

@app.route('/stop_message')
def stop_message():
    global sending_messages
    if sending_messages:
        sending_messages = False
        return 'Messages sending stopped.'
    else:
        return 'No messages are being sent.'

if __name__ == '__main__':
    app.run(debug=True)
