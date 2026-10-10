"""
Добавление пользователей Telegram по никам из Excel.

Режимы:
  MODE = "contacts" — добавить в контакты (как в исходном примере);
  MODE = "group"    — пригласить в вашу группу/канал (вы должны быть админом).

Запуск:  python add_from_excel.py
Результаты пишутся в results.csv; при повторном запуске уже обработанные
ники пропускаются, так что скрипт можно спокойно перезапускать.
"""
import asyncio
import csv
import os
import random
import re

import pandas as pd
from telethon import TelegramClient, errors, functions, types

# ====== НАСТРОЙКИ ======
API_ID = 1234567                 # с my.telegram.org -> API development tools
API_HASH = "твоя_api_hash"
PHONE = "+79990000000"

EXCEL_FILE = "users.xlsx"        # ники в первом столбце (с @ или без)
MODE = "contacts"                # "contacts" или "group"
TARGET_GROUP = "my_group"        # для MODE="group": @ник группы или ссылка t.me/...

DELAY_MIN, DELAY_MAX = 8, 20     # пауза между пользователями, сек
DAILY_LIMIT = 40                 # сколько обработать за один запуск
RESULTS_FILE = "results.csv"
# =======================

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,32}$")
HEADER_WORDS = {"username", "usernames", "ник", "ники", "nick", "login", "логин"}


def read_usernames(path):
    # header=None — иначе pandas считает первую строку заголовком и теряет первый ник
    df = pd.read_excel(path, header=None, dtype=str)
    result, seen = [], set()
    for raw in df.iloc[:, 0].dropna():
        name = str(raw).strip()
        name = re.sub(r"^(https?://)?(t\.me|telegram\.me)/", "", name, flags=re.I)
        name = name.lstrip("@").strip("/")
        if name.lower() in HEADER_WORDS:
            continue
        if not USERNAME_RE.match(name):
            print(f"Пропуск: «{raw}» — не похоже на ник")
            continue
        if name.lower() not in seen:
            seen.add(name.lower())
            result.append(name)
    return result


def load_done():
    if not os.path.exists(RESULTS_FILE):
        return set()
    with open(RESULTS_FILE, encoding="utf-8") as f:
        return {row["username"].lower() for row in csv.DictReader(f)}


def save_result(username, status, details=""):
    new_file = not os.path.exists(RESULTS_FILE)
    with open(RESULTS_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["username", "status", "details"])
        w.writerow([username, status, details])


async def add_one(client, user, group):
    if MODE == "contacts":
        # client.add_contact в Telethon не существует — нужен прямой запрос
        await client(functions.contacts.AddContactRequest(
            id=user,
            first_name=user.first_name or user.username,
            last_name=user.last_name or "",
            phone="",
            add_phone_privacy_exception=False,
        ))
        return "added", ""

    if isinstance(group, types.Channel):  # супергруппа или канал
        res = await client(functions.channels.InviteToChannelRequest(group, [user]))
        if getattr(res, "missing_invitees", None):
            return "privacy", "не разрешает приглашать себя"
    else:  # обычная (старая) группа
        await client(functions.messages.AddChatUserRequest(group.id, user, fwd_limit=0))
    return "added", ""


async def main(client):
    usernames = read_usernames(EXCEL_FILE)
    done = load_done()
    todo = [u for u in usernames if u.lower() not in done][:DAILY_LIMIT]
    print(f"В файле ников: {len(usernames)}, уже обработано: {len(done)}, "
          f"в этот запуск: {len(todo)}")

    group = await client.get_entity(TARGET_GROUP) if MODE == "group" else None

    for i, username in enumerate(todo, 1):
        prefix = f"{i}/{len(todo)} @{username}:"
        while True:  # цикл нужен, чтобы после FloodWait повторить того же человека
            try:
                user = await client.get_entity(username)
                if not isinstance(user, types.User):
                    status, details = "skip", "это не пользователь (канал/группа)"
                else:
                    status, details = await add_one(client, user, group)
            except errors.FloodWaitError as e:
                print(f"{prefix} лимит Telegram, ждём {e.seconds} сек...")
                await asyncio.sleep(e.seconds + 5)
                continue
            except errors.PeerFloodError:
                print("Telegram пометил действия как спам (PeerFlood). "
                      "Остановка — попробуйте через сутки или больше.")
                return
            except (errors.UsernameNotOccupiedError, errors.UsernameInvalidError, ValueError):
                status, details = "not_found", "ник не существует"
            except (errors.UserPrivacyRestrictedError, errors.UserNotMutualContactError):
                status, details = "privacy", "настройки приватности"
            except errors.UserAlreadyParticipantError:
                status, details = "already", "уже в группе"
            except errors.RPCError as e:
                status, details = "error", type(e).__name__
            break

        print(f"{prefix} {status} {details}")
        save_result(username, status, details)
        # asyncio.sleep, а не time.sleep — иначе блокируется соединение клиента
        await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    print(f"Готово. Подробности в {RESULTS_FILE}")


if __name__ == "__main__":
    client = TelegramClient("session_name", API_ID, API_HASH)
    with client.start(phone=PHONE):  # при первом запуске спросит код из Telegram
        client.loop.run_until_complete(main(client))
