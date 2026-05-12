import os
import json
import time
import requests
from flask import Flask, request, Response
from threading import Thread

app = Flask(__name__)

# ===== НАСТРОЙКИ (ЗАМЕНИ НА СВОИ) =====
VK_TOKEN = os.environ.get("VK_TOKEN")
ADMIN_ID = 1076312001
GROUP_ID = 237327488
CONFIRMATION_CODE = "0c9c7a75"
# ======================================

DATA_FILE = "broadcast_data.json"

# Загрузка данных из файла
def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {"chats": [], "promo_text": "Привет! Это тестовая рассылка."}
        save_data(default_data)
        return default_data
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"chats": [], "promo_text": "Привет! Это тестовая рассылка."}

# Сохранение данных в файл
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Отправка сообщения
def send_message(peer_id, text):
    url = "https://api.vk.com/method/messages.send"
    params = {
        "access_token": VK_TOKEN,
        "v": "5.131",
        "peer_id": peer_id,
        "message": text,
        "random_id": 0
    }
    try:
        requests.post(url, params=params)
        return True
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return False

# ===== РАССЫЛКА КАЖДЫЕ 3 МИНУТЫ =====
def broadcast_loop():
    while True:
        time.sleep(180)  # 3 минуты
        
        bot_data = load_data()
        
        if bot_data.get("chats") and len(bot_data["chats"]) > 0:
            print(f"📤 Рассылка в {len(bot_data['chats'])} чатов")
            print(f"   Текст: {bot_data['promo_text']}")
            
            for chat_id in bot_data["chats"]:
                send_message(chat_id, bot_data["promo_text"])
                time.sleep(1)

broadcast_thread = Thread(target=broadcast_loop)
broadcast_thread.daemon = True
broadcast_thread.start()
# ===================================

@app.route('/webhook', methods=['POST'])
def webhook():
    bot_data = load_data()
    data = request.get_json()
    
    # Подтверждение сервера
    if data.get('type') == 'confirmation':
        return Response(CONFIRMATION_CODE, status=200, mimetype='text/plain')
    
    # Обработка сообщений
    if data.get('type') == 'message_new':
        msg = data['object']['message']
        user_id = msg.get('from_id')
        text = msg.get('text', '')
        peer_id = msg.get('peer_id')
        
        # Команда .текст (только админ в ЛС)
        if user_id == ADMIN_ID and peer_id == user_id and text.startswith('.текст '):
            new_text = text[7:]  # убираем ".текст "
            bot_data['promo_text'] = new_text
            save_data(bot_data)
            send_message(peer_id, f"✅ Текст рассылки обновлен!\n\nНовый текст: {new_text}")
            print(f"📝 Текст обновлен: {new_text}")
            return 'ok'
        
        # Команда .чаты (показать список чатов)
        if user_id == ADMIN_ID and peer_id == user_id and text == '.чаты':
            if bot_data.get('chats') and len(bot_data['chats']) > 0:
                chats_list = "\n".join([f"- {chat_id}" for chat_id in bot_data['chats']])
                send_message(peer_id, f"📋 Список чатов в рассылке:\n{chats_list}\n\nВсего: {len(bot_data['chats'])}")
            else:
                send_message(peer_id, "📭 Список чатов пуст.\n\nДобавьте бота в беседу, и он автоматически добавится в рассылку.")
            return 'ok'
        
        # Команда .удалить (удалить чат из рассылки)
        if user_id == ADMIN_ID and peer_id == user_id and text.startswith('.удалить '):
            try:
                chat_id = int(text[9:])
                if chat_id in bot_data['chats']:
                    bot_data['chats'].remove(chat_id)
                    save_data(bot_data)
                    send_message(peer_id, f"✅ Чат {chat_id} удален из рассылки.")
                else:
                    send_message(peer_id, f"❌ Чат {chat_id} не найден в списке.")
            except ValueError:
                send_message(peer_id, "❌ Укажите корректный ID чата.\n\nПример: .удалить 2000000001")
            return 'ok'
        
        # Добавление чата, когда бота пригласили в беседу
        if 'action' in msg and msg['action'].get('type') == 'chat_invite_user':
            invited_id = msg['action'].get('member_id')
            if invited_id == -GROUP_ID:
                if peer_id not in bot_data['chats']:
                    bot_data['chats'].append(peer_id)
                    save_data(bot_data)
                    send_message(peer_id, "✅ Чат добавлен в рассылку!\n\nБот будет отправлять сообщения каждые 3 минуты.")
                    print(f"➕ Чат {peer_id} добавлен в рассылку")
                else:
                    send_message(peer_id, "ℹ️ Этот чат уже в рассылке.")
            return 'ok'
    
    return 'ok'

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
