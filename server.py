import socket

def run_server():
    # 1. Create a TCP socket (SOCK_STREAM implies TCP)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # 2. Bind the socket to your local machine address and an open port
    host = '127.0.0.1' 
    port = 65432
    server_socket.bind((host, port))
    
    # 3. Listen for incoming client connections
    server_socket.listen(1)
    print(f"[*] Server listening on {host}:{port}...")
    
    # 4. Accept a connection from a client
    client_socket, client_address = server_socket.accept()
    print(f"[+] Connected to client at: {client_address}")
    
    try:
        while True:
            # Receive data sent from the client (buffer size 1024 bytes)
            data = client_socket.recv(1024)
            if not data:
                break # Client disconnected
                
            message = data.decode('utf-8')
            print(f"[Received] {message}")
            
            # Send a confirmation response back to the client
            response = f"Server processed: {message}"
            client_socket.sendall(response.encode('utf-8'))
            
    except ConnectionResetError:
        print("[-] Client unexpectedly disconnected.")
    finally:
        # Clean up the connections
        client_socket.close()
        server_socket.close()
        print("[*] Server shut down.")

if __name__ == "__main__":
    run_server()
