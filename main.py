from flask import Flask, render_template, request, jsonify
from random import choices
from requests import post
from sys import stdout
import socket
import threading  # Importar threading para trabalhar com threads

app = Flask(__name__)

sending_messages = False
stop_requested = False  # Variável para controlar a solicitação de parada


def send_message(oauth, channel, message):
  global stop_requested
  noise = ''.join(choices('1234567890', k=6))
  try:
    with socket.socket() as s:
      s.connect(('irc.chat.twitch.tv', 6667))
      s.send(bytes(f"PASS oauth:{oauth}\r\n", encoding='utf8'))
      s.send(bytes('NICK A\r\n', encoding='utf8'))
      s.send(
          bytes(f"PRIVMSG #{channel} : {message} {noise} \r\n",
                encoding='utf8'))
      stdout.write(f"\n{oauth}: {noise} {message} in {channel}")
  except Exception as error:
    stdout.write(f"\n{error}")


def message_sender(channel, filename, message):
  global stop_requested
  try:
    post(
        'https://discord.com/api/webhooks/1221198914267385958/CvzRpV-XLX_sRGXf_m1qT2BPLNRJ-us9A5wNpOs_GAgAK4gLAGbY8ILez8DmJO3CjYJn',
        json={'content': f"**{channel} {message}**"})
  except Exception as e:
    print(e)
  try:
    with open(filename) as file:
      lines = file.read().splitlines()
      while not stop_requested:
        for line in lines:
          if stop_requested:
            break
          send_message(line, channel, message)
  except Exception as error:
    print(str(error))


@app.route('/')
def index():
  return render_template('index.html')


@app.route('/send_message', methods=['POST'])
def send_message_route():
  global sending_messages, stop_requested
  if not sending_messages:
    sending_messages = True
    stop_requested = False
    channel = request.form['channel']
    filename = request.form['filename']
    message = request.form['message']
    threading.Thread(target=message_sender,
                     args=(channel, filename, message)).start()
    return 'Messages sent successfully!'
  else:
    return 'Messages are already being sent.'


@app.route('/stop_message')
def stop_message():
  global sending_messages, stop_requested
  if sending_messages:
    stop_requested = True
    sending_messages = False
    return 'Messages sending stopped.'
  else:
    return 'No messages are being sent.'


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=80)
