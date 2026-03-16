
import socket, ssl, time, os

SERVER_IP   = "192.168.1.157"
SERVER_PORT = 65432
CERT_FILE   = "cert.pem"
INBOX_FILE  = "inbox.txt"
OUTBOX_FILE = "outbox.txt"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_REQUIRED
ctx.load_verify_locations(cafile=CERT_FILE)

def wait_for_message():
    if os.path.exists(INBOX_FILE):
        with open(INBOX_FILE, "r") as f:
            msg = f.read().strip()
        os.remove(INBOX_FILE)
        return msg
    return None

def save_response(response):
    with open(OUTBOX_FILE, "w") as f:
        f.write(response)

try:
    with socket.create_connection((SERVER_IP, SERVER_PORT)) as sock:
        with ctx.wrap_socket(sock, server_hostname=SERVER_IP) as ssock:
            print("🔐 Connected. Waiting for messages...")

            while True:
                msg = wait_for_message()
                if msg:
                    print(f"📨 You: {msg}")
                    ssock.sendall(msg.encode())

                    if msg == "/exit":
                        print("👋 Disconnected.")
                        break

                    response = ssock.recv(1024).decode()
                    print("🤖 Assistant:", response)
                    save_response(response)

                time.sleep(1)

except Exception as e:
    print("❌ Error:", e)
