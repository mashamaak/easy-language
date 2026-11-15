import os
import requests
from flask import Flask, request, render_template_string
import re

app = Flask(__name__)

# Ключи берутся из переменных окружения (на Render вы их настроите)
YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.environ.get("YANDEX_FOLDER_ID")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Упроститель юридических текстов</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; background-color: #8c9dad; color: #3E3630; }
        h1 { color: #3E3630; text-align: center; }
        .container { background: #f4efe7; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        textarea { width: 100%; height: 150px; padding: 15px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; resize: vertical; }
        button { background: #C7D3DB; color: #3E3630; padding: 12px 24px; border: none; cursor: pointer; font-size: 16px; border-radius: 5px; width: 100%; margin-top: 15px; transition: background 0.3s; }
        button:hover { background: #adbdc7; }
        .result { margin-top: 25px; padding: 20px; background: #f4efe7; border-left: 5px solid #faf9f7; border-radius: 5px; }
        .error { color: #e74c3c; margin-top: 15px; font-weight: bold; }
        .loader { display: none; text-align: center; margin-top: 15px; color: #7f8c8d; }
        .result p {
            white-space: pre-wrap;
    </style>
</head>
<body>
    <div class="container">
        <h1>Упроститель юридических текстов</h1>
        <p>Вставьте сложный юридический текст, и система перепишет его простым языком.</p>
        <form method="POST" onsubmit="document.getElementById('loader').style.display='block';">
            <textarea name="text" placeholder="Вставьте текст здесь...">{{ text or '' }}</textarea>
            <button type="submit">Упростить</button>
            <div id="loader" class="loader">⏳ Обработка текста нейросетью...</div>
        </form>
        {% if result %}
        <div class="result">
            <h3>Упрощённый текст:</h3>
            <p>{{ result | safe }}</p>
        </div>
        {% endif %}
        {% if error %}
        <p class="error">{{ error }}</p>
        {% endif %}
    </div>
</body>
</html>
"""


def format_result(text):
    # Убираем возможные остатки Markdown
    text = re.sub(r'^###\s*(.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s*(.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^#\s*(.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    # Заменяем переносы строк на <br>
    text = text.replace('\n', '<br>')
    return text


def simplify_with_yandex(text):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"Твоя задача – упростить текст, сохранив его точный смысл и всю важную информацию, но сделав его понятным для человека с базовым уровнем образования (9 классов школы). Ты должен следовать принципам ясного языка. Соблюдай следующие правила: Замени все термины, канцеляризмы и сложные слова на простые, частотные синонимы. Если термин невозможно заменить без потери значения, добавь сразу после него краткое объяснение в скобках. Избегай заимствований, если есть понятные русские аналоги. Замени все пассивные конструкции на активные. Избегай цепочек родительного падежа. Перестрой их, используя предлоги. Замени отглагольные существительные на глаголы. Обращайся к читателю на «вы», чтобы текст был персонализированным. Раздели все длинные предложения на короткие. Одно предложение = одна мысль. Избегай сложноподчиненных предложений с несколькими придаточными, разбей их на несколько простых. Убери все причастные и деепричастные обороты, заменив их на простые предложения. Используй прямой порядок слов. Добавь описательные заголовки для каждого смыслового блока. Используй нумерованные списки для последовательности действий. Используй маркированные списки для перечислений. Не теряй ни одной важной детали из исходного текста. Все сроки, условия и требования должны быть сохранены. Изменяй только форму, но не содержание. Верни только упрощённый текст без комментариев, без Markdown, без символов #, без звёздочек. Используй обычные абзацы и переносы строк..\n\nТекст: {text}"
    
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite/latest",
        "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": 2000},
        "messages": [
            {"role": "system", "text": "Ты — помощник юриста, который объясняет сложные законы простым языком."},
            {"role": "user", "text": prompt}
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        raw_text = response.json()["result"]["alternatives"][0]["message"]["text"]
        return format_result(raw_text)
    else:
        raise Exception(f"Ошибка API: {response.status_code} — {response.text}")

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    text = ""
    if request.method == "POST":
        text = request.form.get("text", "")
        if not text.strip():
            error = "Пожалуйста, введите текст."
        else:
            try:
                result = simplify_with_yandex(text)
            except Exception as e:
                error = str(e)
    return render_template_string(HTML_TEMPLATE, result=result, error=error, text=text)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
