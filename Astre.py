import os
import subprocess
import tempfile
import shutil
import telebot
import threading
import time

BOT_TOKEN = "8222963966:AAG6-qG4cArKF2eHj1D8HsQ4v-xiBgaBAp8"
REPO_URL = "https://github.com/Astre06/RavTest.git"

bot = telebot.TeleBot(BOT_TOKEN)
password_storage = {"password": None}
main_process = None
loader_thread = None
repo_path_global = None  # global to track cloned repo folder

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Send /password <your_password> to unlock the code archive, or /stop to halt execution.")

@bot.message_handler(commands=['password'])
def receive_password(message):
    global loader_thread
    try:
        password = message.text.split()[1]
    except IndexError:
        bot.reply_to(message, "Usage: /password <your_password>")
        return
    if password_storage["password"] is None:
        password_storage["password"] = password
        bot.reply_to(message, "Password received. Starting extraction...")
        if loader_thread is None or not loader_thread.is_alive():
            loader_thread = threading.Thread(target=loader, daemon=True)
            loader_thread.start()
    else:
        bot.reply_to(message, "Password already set and running.")

@bot.message_handler(commands=['stop'])
def stop_command(message):
    global main_process, repo_path_global
    if main_process and main_process.poll() is None:
        main_process.terminate()
        main_process.wait()
        bot.reply_to(message, "Main script stopped successfully.")
        # Now immediately cleanup
        if repo_path_global and os.path.exists(repo_path_global):
            shutil.rmtree(repo_path_global, ignore_errors=True)
            repo_path_global = None
            password_storage["password"] = None
            main_process = None
            bot.reply_to(message, "Temporary files cleaned up.")
    else:
        bot.reply_to(message, "No main script is currently running.")

def clone_repo(repo_url):
    temp_dir = tempfile.mkdtemp()
    hidden_dir = os.path.join(temp_dir, ".ravtest_hidden")
    subprocess.run(["git", "clone", repo_url, hidden_dir], check=True)
    return hidden_dir

def extract_rar_with_password(repo_path, password, extract_to):
    unrar_exe = "unrar"  # ensure installed on VPS
    rar_path = os.path.join(repo_path, "Astre.rar")
    cmd = [unrar_exe, "x", f"-p{password}", "-y", rar_path, extract_to]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Extraction failed: {result.stderr}")

def run_main_script(extract_root):
    global main_process
    entries = [e for e in os.listdir(extract_root) if os.path.isdir(os.path.join(extract_root, e))]
    if not entries:
        raise RuntimeError("No directory found inside extracted folder")
    inner_folder = os.path.join(extract_root, entries[0])
    main_py = os.path.join(inner_folder, "main.py")
    if not os.path.isfile(main_py):
        raise RuntimeError(f"main.py not found in {inner_folder}")
    main_process = subprocess.Popen(["python3", main_py])

def loader():
    global repo_path_global
    repo_path_global = clone_repo(REPO_URL)
    try:
        extract_dir = os.path.join(repo_path_global, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        while password_storage["password"] is None:
            time.sleep(3)
        extract_rar_with_password(repo_path_global, password_storage["password"], extract_dir)
        run_main_script(extract_dir)
        main_process.wait()
    except Exception as e:
        print(f"Loader error: {e}")
    finally:
        if repo_path_global and os.path.exists(repo_path_global):
            shutil.rmtree(repo_path_global, ignore_errors=True)
            repo_path_global = None
        password_storage["password"] = None
        global main_process
        main_process = None

def main():
    bot.polling()

if __name__ == '__main__':
    main()
