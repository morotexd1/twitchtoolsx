from flask import Flask, render_template, request, redirect, url_for
from random import choices
from requests import post
import socket
import threading
import random
import string
import time
import requests

app = Flask(__name__)

sending_messages = False
stop_requested = False
follow_info = {}
last_followed_tokens = {}


CLIENT_ID = 'ue6666qo983tsx6so1t0vnawi233wa'

# Adicionando variável global para controlar o processo de seguir os usuários
following_users_process = None


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
                    'version': 1,
                    'sha256Hash': '1a821ba00dba99f6d807085f42952bde795997276f4cdb7fdc952e322b810244',
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
            if user_id not in follow_info:
                follow_info[user_id] = {'tokens': []}
            follow_info[user_id]['tokens'].append(token.split(':')[0])

            # Atualize last_followed_tokens
            last_followed_tokens['user_id'] = user_id
            last_followed_tokens['tokens'] = [token.split(':')[0]]

            return True  # Indicate success
        else:
            return False  # Indicate failure


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
        print(f"\n{error}")


@app.route('/')
def index():
    return render_template('index.html', follow_info=follow_info, last_followed_tokens=last_followed_tokens)


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


@app.route('/stop-following-all')
def stop_following_all():
    global stop_requested, follow_info
    stop_requested = True
    global following_users_process
    if following_users_process is not None and following_users_process.is_alive():
        following_users_process.join()
        following_users_process = None
    follow_info.clear()
    last_followed_tokens.clear()
    return redirect(url_for('index'))


@app.route('/follow_users', methods=['POST'])
def follow_users():
    global following_users_process, stop_requested
    if following_users_process is not None and following_users_process.is_alive():
        return 'Following process is already running.', 400

    # Reset stop_requested before starting a new following process
    stop_requested = False

    users = request.form['users'].split('\n')
    tokens_file = request.form['tokensFile']
    twitch_session = TwitchSession()
    targets_id = [twitch_session.get_user_id(user) for user in users]
    tokens = open(tokens_file).read().splitlines()
    random.shuffle(tokens)

    following_users_process = threading.Thread(
        target=follow_users_process_handler,
        args=(twitch_session, targets_id, tokens))
    following_users_process.start()

    return 'Following users...'


def follow_users_process_handler(twitch_session, targets_id, tokens):
    global stop_requested
    for user_id in targets_id:
        if stop_requested:
            break
        for token in tokens:
            twitch_session.follow(user_id, token.split(':')[0])
            if stop_requested:
                break


def main():
    app.run(host='0.0.0.0', port=80)


if __name__ == '__main__':
    main()
