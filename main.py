import os
import sys
import git
import requests
from dotenv import load_dotenv
from imgurpython import ImgurClient
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage, ImageSendMessage

load_dotenv()

chika_repo = git.cmd.Git(os.environ['CHIKA_REPOSITORY'])

admin = os.environ['CHIKA_ADMIN'].split(',')

app = Flask(__name__)
line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])

imgur_client = ImgurClient(
    os.environ['IMGUR_CLIENT_ID'], 
    os.environ['IMGUR_CLIENT_SECRET'],
    os.environ['IMGUR_ACCESS_TOKEN'],
    os.environ['IMGUR_REFRESH_TOKEN']
)

flag_removebg = 0

def getContent(msg_id):
    message_content = line_bot_api.get_message_content(str(msg_id))
    try:
        os.mkdir('saved_content')
    except:
        pass
    with open('saved_content/' + str(msg_id), 'wb') as f:
        for chunk in message_content.iter_content():
            f.write(chunk)
    return 'saved_content/' + str(msg_id)

def removebgAPI(path):
    print(os.environ['REMOVEBG_KEY'])
    response = requests.post(
        'https://api.remove.bg/v1.0/removebg',
        files = {'image_file':open(path, 'rb')},
        data = {'size':'auto'},
        headers = {'X-API-Key':os.environ['REMOVEBG_KEY']}
    )
    path = path.split('/')
    path[-1] = path[-1] + '_removebg'
    path = '/'.join(path)
    if response.status_code == 200:
        with open(path, 'wb') as out:
            out.write(response.content)
    else:
        print(response.text)
        return 'failed'
    return path

def restart():
    os.execv(sys.executable, ['python3']+sys.argv)

def uploadToImgur(path):
    response = imgur_client.upload_from_path(path)
    link = response['link']
    return link

@app.route('/test', methods=['POST'])
def test():
    return "ok"

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

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    global flag_removebg
    token = event.reply_token
    message = event.message.text
    source = event.source.user_id
    if message == 'chika self pull':
        if source in admin:
            response = chika_repo.pull()
            response = '[CHIKA REPO]\n' + response
            line_bot_api.reply_message(token, TextSendMessage(text=response))
        else:
            line_bot_api.reply_message(token, TextSendMessage(text='who are you?'))
    elif message == 'chika restart':
        if source in admin:
            line_bot_api.reply_message(token, TextSendMessage(text='restarting'))
            restart()
        else:
            line_bot_api.reply_message(token, TextSendMessage(text='who are you?'))
    elif message == 'chika test':
        line_bot_api.reply_message(token, TextSendMessage(text='ok'))
    elif message == 'chika userId':
        line_bot_api.reply_message(token, TextSendMessage(text=str(source)))
    elif message == 'chika removebg':
        if flag_removebg:
            flag_removebg = 0
            line_bot_api.reply_message(token, TextSendMessage(text='removebg off'))
        else:
            flag_removebg = 1
            line_bot_api.reply_message(token, TextSendMessage(text='removebg on'))

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    token = event.reply_token
    message_id = event.message.id
    if flag_removebg:
        path = getContent(message_id)
        path = removebgAPI(path)
        if path == 'failed':
            line_bot_api.reply_message(token, TextSendMessage(text='failed'))
            return
        link = uploadToImgur(path)
        line_bot_api.reply_message(token, ImageSendMessage(original_content_url=link, preview_image_url=link))

@handler.default()
def default(event):
    print(event)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8443, ssl_context=(os.environ['SSL_FULLCHAIN'], os.environ['SSL_PRIVKEY']))
