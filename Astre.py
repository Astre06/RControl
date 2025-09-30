import os
import subprocess
import tempfile
import shutil
import telebot
import threading
import time

BOT_TOKEN = "8383780670:AAGOvwy7ItP-cdF8-suLkNL3jpXsrugJbH8"
REPO_URL = "https://github.com/Astre06/RavTest.git"

bot = telebot.TeleBot(BOT_TOKEN)
password_storage = {"password": None}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Send /password <your_password> to unlock the code archive.")

@bot.message_handler(commands=['password'])
def receive_password(message):
    try:
        password = message.text.split()[1]
    except IndexError:
        bot.reply_to(message, "Usage: /password <your_password>")
        return
    password_storage["password"] = password
    bot.reply_to(message, "Password received. Starting extraction...")

def clone_repo(repo_url):
    temp_dir = tempfile.mkdtemp()
    hidden_dir = os.path.join(temp_dir, ".ravtest_hidden")
    subprocess.run(["git", "clone", repo_url, hidden_dir], check=True)
    return hidden_dir

def extract_rar_with_password(repo_path, password, extract_to):
    unrar_exe = "unrar"  # Linux unrar, ensure installed on your VPS
    rar_path = os.path.join(repo_path, "Astre.rar")
    cmd = [unrar_exe, "x", f"-p{password}", "-y", rar_path, extract_to]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Extraction failed: {result.stderr}")

def run_main_script(extract_root):
    # Detect folder inside extract_root (your archive extracts to a folder)
    entries = [e for e in os.listdir(extract_root) if os.path.isdir(os.path.join(extract_root, e))]
    if not entries:
        raise RuntimeError("No directory found inside extracted folder")
    inner_folder = os.path.join(extract_root, entries[0])
    main_py = os.path.join(inner_folder, "main.py")
    if not os.path.isfile(main_py):
        raise RuntimeError(f"main.py not found in {inner_folder}")
    subprocess.run(["python3", main_py])

def cleanup(path):
    shutil.rmtree(path, ignore_errors=True)

def loader():
    repo_path = clone_repo(REPO_URL)
    try:
        print("Waiting for password via Telegram bot...")
        while password_storage["password"] is None:
            time.sleep(3)
        extract_dir = os.path.join(repo_path, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        extract_rar_with_password(repo_path, password_storage["password"], extract_dir)
        run_main_script(extract_dir)
    finally:
        cleanup(repo_path)

def main():
    threading.Thread(target=loader, daemon=True).start()
    bot.polling()

if __name__ == '__main__':
    main()


