from getpass import getpass
from hugchat.login import Login

email = input("Hugging Face email: ")
password = getpass("Hugging Face password: ")

login = Login(email, password)
login.login(cookie_dir_path="backend/", save_cookies=True)

print("HugChat cookies saved.")