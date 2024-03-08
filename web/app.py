import requests
import json
from flask import Flask, request, abort,render_template
from linebot import LineBotApi
from linebot.models import *
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
from openai import OpenAI
from pyngrok import ngrok, conf


# 設定token
# ngrok.set_auth_token("申請的AuthToken")
ngrok.set_auth_token("")
conf.get_default().region = "jp"

# 自訂連線函式
port = 5000
public_url = ngrok.connect(port, bind_tls=True).public_url
print(" * ngrok tunnel \"{}\" -> \"http://127.0.0.1:{}/\"".format(public_url, port))



channel_access_token = ""


"""建立圖文選單"""

rich_menu_object = {
    "size": {"width": 2500,"height": 1686},
    "selected": True,
    "name": "功能選單",
    "chatBarText": "功能選單",
    "areas":[
        {
        "bounds": {"x": 0, "y": 0, "width": 1250, "height": 843},
        "action": {"type": "uri","label": "關於我們","uri": f"{public_url}/web"}
        },
        {
        "bounds": {"x": 1250, "y": 0, "width": 1250, "height": 843},
        "action": {"type": "message", "text": "問答須知"}
        },
        {
        "bounds": {"x": 0, "y": 843, "width": 1250, "height": 843},
        "action": {"type": "uri","label": "網頁版","uri": f"{public_url}/web"}
        },
        {
        "bounds": {"x": 1250, "y": 843, "width": 1250, "height": 843},
        "action": {"type": "message", "text": "推薦親友"}
        }
    ]
}

# Create a rich menu
create_rich_menu_url = "https://api.line.me/v2/bot/richmenu"
create_rich_menu_headers = {
    "Authorization": "Bearer " + channel_access_token,
    "Content-Type": "application/json"
}
create_rich_menu_response = requests.post(create_rich_menu_url, headers=create_rich_menu_headers, json=rich_menu_object)
create_rich_menu_response.raise_for_status()

# Get the rich menu ID
rich_menu_id = create_rich_menu_response.json()["richMenuId"]

# Upload the rich menu image
rich_menu_image_path = "./static/img/richmenu.jpg"
upload_rich_menu_image_url = "https://api-data.line.me/v2/bot/richmenu/" + rich_menu_id + "/content"
upload_rich_menu_image_headers = {
    "Authorization": "Bearer " + channel_access_token,
    "Content-Type": "image/jpeg"
}
upload_rich_menu_image_data = open(rich_menu_image_path, "rb").read()
upload_rich_menu_image_response = requests.post(upload_rich_menu_image_url, headers=upload_rich_menu_image_headers, data=upload_rich_menu_image_data)
upload_rich_menu_image_response.raise_for_status()

# Set the default rich menu
set_default_rich_menu_url = "https://api.line.me/v2/bot/user/all/richmenu/" + rich_menu_id
set_default_rich_menu_headers = {
    "Authorization": "Bearer " + channel_access_token
}
set_default_rich_menu_response = requests.post(set_default_rich_menu_url, headers=set_default_rich_menu_headers)
set_default_rich_menu_response.raise_for_status()

# Print the result
print("Rich menu created and uploaded successfully!")



def OpenAI_process_data(user_input):
    client = OpenAI(organization = 'org-mfIE2DbaoeBfo2Vk7S79qO41', api_key='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')
    response = client.chat.completions.create(
        model="ft:gpt-3.5-turbo-1106:personal::8cS9dlql",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_input}
        ]
    )
    return response.choices[0].message.content



app = Flask(__name__)

line_bot_api = LineBotApi('EQuOoOUJj7h3mLF6/vvWSpw2f8AfvcPOCTjjvo042ldMFtQb8+RpQKuGXJfcQgbh2nLkqjB0RuwjXPAqywizBdW1kJze65nr2K3jltK0QqlIHqJ5nJK47KkoCbNl90fePBztntpo5IA5tnErBeAGWwdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('8c1902879f7fedb2f905ba1b79ad02b1')

@app.route('/web' , methods=["GET"]) 
def index_page():
    return render_template('index.html')

@app.route('/process_data' , methods=["POST"])
def process_data():
    Udata = request.form.get("UserInput")
    Rdata = OpenAI_process_data(Udata)
    return {"RobotReply":Rdata}


@app.route("/", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text
    
    if user_input == "問答須知":
        line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="請用繁體中文明確敘述事件經過"))

    if user_input == "推薦親友":
        line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="加入法律智能小幫手連結: https://lin.ee/vNsToGI"))


    else:
        # OpenAi API 回傳的答案
        generated_text = OpenAI_process_data(user_input).strip()

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=generated_text)
        )






if __name__ == "__main__":
    app.run()