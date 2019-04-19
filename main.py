import os
import git
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

load_dotenv()

repo = git.cmd.Git(os.environ['GIT_REPOSITORY'])

admin = os.environ['CHIKA_ADMIN'].split(',')

app = Flask(__name__)
line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])

@app.route('/callback', methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret")
        abort(400)

    return 'OK'

@app.route('/')
def home():
    return 'ok'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    token = event.reply_token
    message = event.message.text
    source = event.source.user_id
    if message == 'pull':
        if source in admin:
            response = repo.pull()
            line_bot_api.reply_message(token, TextSendMessage(text=response))
    elif message == 'ok':
        line_bot_api.reply_message(token, TextMessage(text='ok'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8443, ssl_context=('/etc/letsencrypt/live/rahandi.southeastasia.cloudapp.azure.com/fullchain.pem', '/etc/letsencrypt/live/rahandi.southeastasia.cloudapp.azure.com/privkey.pem'))
