import socket, ssl, sys

SERVER_IP   = "192.168.1.157"  # Replace with your server’s LAN IP
SERVER_PORT = 65432

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_REQUIRED
ctx.load_verify_locations(cafile="cert.pem")  # Trust the server's cert

with socket.create_connection((SERVER_IP, SERVER_PORT)) as sock:
    with ctx.wrap_socket(sock, server_hostname=SERVER_IP) as ssock:
        print("🔐 Connected securely to assistant server.\n(Type /exit to quit)\n")

        while True:
            # Collect input either from command-line arg or interactively
            if len(sys.argv) > 1:
                message = sys.argv[1]
                sys.argv = sys.argv[:1]  # Use it once, then switch to input
            else:
                message = input("📝 You: ")

            if not message:
                continue
            ssock.sendall(message.encode())

            if message == "/exit":
                print("👋 Disconnected.")
                break

            try:
                response = ssock.recv(1024)
                if not response:
                    print("⚠️ Server closed connection.")
                    break
                print("🤖 Assistant:", response.decode())
            except Exception as e:
                print("❌ Error receiving reply:", e)
                break

