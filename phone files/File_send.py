import socket, ssl, os, sys

SERVER_IP   = "192.168.1.157"
SERVER_PORT = 65432
CERT_FILE   = "cert.pem"
INBOX_FILE  = "inbox.txt"
OUTBOX_FILE = "outbox.txt"

if len(sys.argv) < 3:
    print("⚠️ No file path provided.")
    sys.exit(1)

file_path = sys.argv[1]
ssl_sock = sys.argv[2]
print(file_path)
print(ssl_sock)

if not os.path.isfile(file_path):
    print(f"❌ File not found: {file_path}")
    sys.exit(1)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_REQUIRED
ctx.load_verify_locations(cafile=CERT_FILE)

try:
    with socket.create_connection((SERVER_IP, SERVER_PORT)) as sock:
        with ctx.wrap_socket(sock, server_hostname=SERVER_IP) as ssock:
            print("🔐 Connected. Waiting for messages...")

            while True:
                try:
                    with open(file_path, 'rb') as f:
                        while chunk := f.read(4096):
                            ssl_sock.sendall(chunk)
                        ssl_sock.sendall(b"<EOF>")  # Signal end of file
                    print(f"✅ File '{os.path.basename(file_path)}' sent successfully.")
                except Exception as e:
                    print(f"⚠️ Error sending file: {e}")
                    sys.exit(1)

except Exception as e:
    print("❌ Error:", e)
