#imports
import socket, ssl, keyboard
from Assistant import SimpleAI
import tkinter as tk
from time import sleep

# Easiest way to get the laptop's local IP address
ip = socket.gethostbyname(socket.gethostname())


#function that makes widget on the desktop so that it is easily known if the serve ris running locally
def show_widget():
    global root
    root = tk.Tk()
    root.title("Status")
    root.overrideredirect(True)    

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    width, height = 150, 50
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    label = tk.Label(root, text= f"ip: {ip}", bg="lightgreen", font=("Arial", 12))
    label.pack(expand=True, fill='both')
    root.attributes("-topmost", False)  # Keep on top
    root.update()
    
    sleep(10)
    label.config(text="Server Running...\nctrl+alt+d")
    root.update()
#function that destroys the widget 
def hide_widget():
    if root:
        root.destroy()

#make an Ai instance and makes it known to be run on the server
Ai = SimpleAI()
Ai.tools.serverRun = True

#removes any possible hotkey for ctrl+alt+d
try:
    keyboard.remove_hotkey("ctrl+alt+d")
except:    pass

#variable for server loop
global serverrunning
serverrunning = True

#function to stop the server loop
def stop_server():
    global serverrunning
    serverrunning = False

#assign the hotkey to stop the server loop for ctrl+alt+d
keyboard.add_hotkey("ctrl+alt+d", stop_server)

HOST = '0.0.0.0'
PORT = 65432
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
#Server connetion and loop
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind((HOST, PORT))
    sock.listen(5)
    sock.settimeout(1.0)  # loop remains responsive to Esc

    print(f"🔐 TLS server listening on port {PORT}. Press Esc to stop.\n")
    show_widget()

    with context.wrap_socket(sock, server_side=True) as ssock:
        while serverrunning:
            try:
                conn, addr = ssock.accept()
                print("✅ Connected by", addr)

                with conn:
                    conn.settimeout(1.0)
                    while serverrunning:
                        if keyboard.is_pressed("esc"):
                            print("🛑 Escape key pressed. Shutting down server.")
                            raise KeyboardInterrupt

                        try:
                            data = conn.recv(1024)
                            if not data or data.decode() == "/exit":
                                print("👋 Client disconnected.")
                                break

                            try:
                                query = data.decode()
                            except UnicodeDecodeError:
                                filename = f"received_file_{addr[0]}_{addr[1]}.bin"
                                with open(filename, "wb") as f:
                                    f.write(data)
                                conn.sendall(f"File saved as {filename}".encode('utf-8'))
                                print(f"💾 Saved binary data to {filename}")
                                continue

                            query = data.decode()
                            if "ai response" in query.lower():
                                if Ai.tools.ai_response == "":
                                    conn.sendall("No Ai response generated yet please try again later.".encode('utf-8'))
                                else:
                                    conn.sendall(Ai.tools.ai_response.encode('utf-8'))
                                    Ai.lastmessage = Ai.tools.ai_response
                                    Ai.tools.ai_response = ""
                                    
                            print("📨 Received:", query)

                            airesponse = Ai.respond(query)
                            Ai.lastmessage = airesponse
                            conn.sendall(airesponse.encode('utf-8'))
                            
                        except socket.timeout:
                            continue
                        except Exception as e:
                            print("⚠️ Error during client session:", e)
                            break

            except socket.timeout:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                print("⚠️ Error accepting connection:", e)

#shut down sequence
hide_widget()
print("🧹 Server shutdown complete.")
