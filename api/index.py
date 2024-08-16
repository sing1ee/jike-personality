from flask import Flask, render_template_string, request, redirect, url_for
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import concurrent.futures
import collections
import time
import os


app = Flask(__name__)

index_html = """
<!-- templates/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jike 人间清醒</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 p-8">
    <div class="max-w-md mx-auto bg-white rounded-xl shadow-md overflow-hidden md:max-w-2xl">
        <div class="md:flex">
            <div class="p-8">
                <div class="uppercase tracking-wide text-sm text-indigo-500 font-semibold">Jike 人间清醒</div>
                <form method="POST" class="mt-4">
                    <input type="text" name="url" placeholder="https://okjk.co/j8R3kn" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                    <div class="tracking-wide text-sm text-indigo-500 font-semibold">链接在即刻 APP 用户页面点击分享之后复制</div>
                    <button type="submit" class="mt-4 px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                        坐稳扶好，去人间
                    </button>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
"""
result_html = """<!-- templates/result.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>清醒了么？</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <div class="bg-gray-100 p-8" id="info">
        <div class="max-w-md mx-auto bg-white rounded-xl shadow-md overflow-hidden md:max-w-2xl mb-8">
            <div class="md:flex">
                <div class="p-8">
                    <div class="uppercase tracking-wide text-sm text-indigo-500 font-semibold">User Information</div>
                    <h2 class="block mt-1 text-lg leading-tight font-medium text-black">{{ user.nickname }}</h2>
                    <p class="mt-2 text-gray-500">{{ user.intro }}</p>
                </div>
            </div>
        </div>

        {% for model in models %}
        <div class="max-w-md mx-auto bg-white rounded-xl shadow-md overflow-hidden md:max-w-2xl mb-8">
            <div class="md:flex">
                <div class="p-8">
                    <div class="uppercase tracking-wide text-sm text-indigo-500 font-semibold">{{ model.name }}</div>
                    <p class="mt-2 text-gray-500">{{ model.text }}</p>
                </div>
            </div>
        </div>
        {% endfor %}
        <div class="max-w-md mx-auto bg-white rounded-xl shadow-md overflow-hidden md:max-w-2xl mb-8">
            <div class="md:flex">
                <div class="p-8">
                    <div class="uppercase tracking-wide text-sm text-indigo-500 font-semibold">
                        <a href="/">让我清醒下</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""


def parse_jike_link(url):
    # 这里应该是解析 jike 链接的逻辑
    # 由于无法直接访问，这里只返回模拟数据
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    nickname = soup.find("div", class_="user-screenname").text
    status = soup.find("div", class_="user-status").text
    description = soup.find("div", class_="brief").text
    # 查找所有 class 为 "text" 的元素
    text_elements = soup.find_all(class_="text")

    # 提取这些元素的文本内容
    text_list = [element.get_text() for element in text_elements]
    return {
        "nickname": nickname,
        "intro": description,
        "status": status,
        "posts": text_list,
    }


client = OpenAI()
user_cache = collections.defaultdict(dict)
model_cache = collections.defaultdict(list)
expire = collections.defaultdict(int)


def get_model_response(model, prompt):
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
        )
        return {"name": model, "text": chat_completion.choices[0].message.content}
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"name": model, "text": f"Error: {str(e)}"}


prompt_template = '''
You are a professional commentator known for your edgy and provocative style. Your task is to look at people's tweets and rate their personalities based on that. Be edgy and provocative, be mean a little. Don't be cringy. Here's a good attempt of a roast: """Alright, let's break this down. You're sitting in a jungle of houseplants, barefoot and looking like you just rolled out of bed. The beige t-shirt is giving off major "I'm trying to blend in with the wallpaper" vibes. And those black pants? They scream "I couldn't be bothered to find something that matches." But hey, at least you look comfortable. Comfort is key, right? Just maybe not when you're trying to make a fashion statement.""" 

profile 和 posts 都来自社交网络：即刻。

Input:

《profile》
@%s
%s
《/profile》

《posts》
%s
《/posts》

Output (请用中文输出):
'''

model = os.getenv("MODEL", "THUDM/glm-4-9b-chat")


def process_data(user_data):
    # 这里应该是处理数据的逻辑
    # 返回模型输出的列表

    prompt = prompt_template % (
        user_data["nickname"],
        user_data["intro"],
        "\n***\n".join(user_data["posts"]),
    )

    return [get_model_response(model, prompt)]


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        if not url:
            url = "https://okjk.co/j8R3kn"
        # if expire[url] != 0 and time.time() - expire[url] > 3600:
        #     del user_cache[url]
        #     del model_cache[url]
        # user_data, model_outputs = None, None
        # if url in user_cache:
        #     user_data = user_cache[url]
        # if url in model_cache:
        #     model_outputs = model_cache[url]
        # if not user_data or not model_outputs:
        #     user_data = parse_jike_link(url)
        #     model_outputs = process_data(user_data)
        #     user_cache[url] = user_data
        #     model_cache[url] = model_outputs
        #     expire[url] = int(time.time())
        # return render_template_string(result_html, user=user_data, models=model_outputs)
        return redirect("/history?url=%s" % url)
    return render_template_string(index_html)


@app.route("/history", methods=["GET"])
def history():
    if request.method == "GET":
        url = request.args.get("url", default="", type=str)
        if expire[url] != 0 and time.time() - expire[url] > 3600:
            del user_cache[url]
            del model_cache[url]
        user_data, model_outputs = {}, []
        if url in user_cache:
            user_data = user_cache[url]
        if url in model_cache:
            model_outputs = model_cache[url]
        if not user_data or not model_outputs:
            user_data = parse_jike_link(url)
            model_outputs = process_data(user_data)
            user_cache[url] = user_data
            model_cache[url] = model_outputs
            expire[url] = int(time.time())
        return render_template_string(result_html, user=user_data, models=model_outputs)
