from flask import Flask, render_template, request, jsonify
from random import choices
from requests import post
from sys import stdout
import socket
import threading
import random
import string
import time
import requests

app = Flask(__name__)

sending_messages = False
stop_requested = False
follow_info = [
]  # Lista para armazenar informações sobre os tokens que seguiram os usuários

CLIENT_ID = 'ue6666qo983tsx6so1t0vnawi233wa'


class UserNotFound(Exception):
  pass


class TwitchHeaders:

  def __init__(self, client_id=None):
    self.client_id = client_id

  def random(self, oauth=None):
    headers = {}
    user_agent = 'Mozilla/5.0 (Linux; Android 7.1.2; SM-G970N Build/N2G47H; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.198 Safari/537.36'
    device_id = random_string(32)
    client_session_id = random_string(16)
    if oauth:
      headers['Authorization'] = f'OAuth {oauth}'

    headers.update({
        'accept': 'application/vnd.twitchtv.v3+json',
        'api-consumer-type': 'mobile; Android/1309000',
        'x-app-version': '13.9.0',
        'User-Agent': user_agent,
        'Client-ID': self.client_id,
        'X-Device-Id': device_id,
        'Client-Session-Id': client_session_id,
        'Origin': 'https://celadon-arztjmkowcbjjgq11.tv.twitch.tv',
        'Referer': 'https://celadon-arztjmkowcbjjgq11.tv.twitch.tv',
    })
    return headers


class TwitchSession:

  def __init__(self):
    self.twitch_headers = TwitchHeaders(CLIENT_ID)

  def gql_request(self, data, token=None, **kwargs):
    return requests.post(
        'https://gql.twitch.tv/gql',
        headers=self.twitch_headers.random(token),
        json=data,
        **kwargs,
    )

  def get_user_id(self, user):
    json_data = [{
        'operationName': 'ChatUser',
        'variables': {
            'login': f'{user}'
        },
        'extensions': {
            'persistedQuery': {
                'version':
                1,
                'sha256Hash':
                '1a821ba00dba99f6d807085f42952bde795997276f4cdb7fdc952e322b810244',
            }
        },
    }]
    response = self.gql_request(data=json_data)
    response_json = response.json()
    try:
      return response_json[0]['data']['user']['id']
    except TypeError as e:
      raise UserNotFound from e

  def follow(self, user_id, token):
    json_data = {
        "query":
        "mutation useFollowChannel_FollowMutation(\n  $input: FollowUserInput!\n) {\n  followUser(input: $input) {\n    follow {\n      user {\n        id\n        __typename\n        self {\n          follower {\n            followedAt\n          }\n        }\n      }\n    }\n  }\n}\n",
        "variables": {
            "input": {
                "disableNotifications": True,
                "targetID": user_id
            }
        }
    }
    response = self.gql_request(data=json_data, token=token)
    if response.status_code == 200:
      follow_info.append(
          f'Token {token.split(":")[0]} followed user {user_id}')
    else:
      print('error', response.status_code, response.text)


def random_string(k=32):
  return ''.join(random.choices(string.hexdigits, k=k))


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
  except Exception as error:
    stdout.write(f"\n{error}")


@app.route('/')
def index():
  return render_template('index.html', follow_info=follow_info)


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


@app.route('/follow_users', methods=['POST'])
def follow_users():
  global follow_info, stop_requested
  follow_info = []  # Limpa a lista de informações de follow
  if not stop_requested:
    users = request.form['users'].split('\n')
    tokens_file = request.form['tokensFile']
    twitch_session = TwitchSession()
    targets_id = [twitch_session.get_user_id(user) for user in users]
    tokens = open(tokens_file).read().splitlines()
    random.shuffle(tokens)

    for user_id in targets_id:
      for token in tokens:
        if stop_requested:
          break
        twitch_session.follow(user_id, token.split(':')[0])

    return 'Following users...'
  else:
    return 'Following users stopped.'


@app.route('/stop_follow')
def stop_follow():
  global stop_requested
  stop_requested = True
  return jsonify(follow_info)


def main():
  app.run(host='0.0.0.0', port=80)


if __name__ == '__main__':
  main()
