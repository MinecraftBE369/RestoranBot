import os
from dotenv import load_dotenv

# Загружаем переменные из .env в окружение Python
load_dotenv()

# === ТОКЕН БОТА ===
# os.getnv() достает значение по ключу из .env
# Если переменной не будет вернется None
BOT_TOKEN = os.getenv("BOT_TOKEN")

# === ID АДМИНОВ ===
# В .env id админов мы храним через запятую
# Поэтому: 
#  1. достаем строку, если пусто - даём ""
#  2. режем строку на список (.split())
#  3. превращаем каждую строчку в число (map())
#  4. превращаем map обратно в нормальный список (list())
ADMINS_IDS = [int(x.strip()) for x in os.getenv("ADMINS_IDS", "").split(",") if x.strip()]

# === ЛОКАЬНЫЙ ПРОКСИ ОТ VPN ===
PROXY_URL = "http://127.0.0.1:10809"