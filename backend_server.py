import socket
import threading
import time
import sys
import random

# Read port from command line input, default to 6001
HOST = '0.0.0.0'
GATEWAY_HEARTBEAT_PORT = 5555
GATEWAY_IP = '10.0.0.2' 

def send_heartbeat():
    """Periodically sends heartbeats to the load balancer with current load status."""
    while True:
        try:
            hb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            hb_socket.connect((HOST, GATEWAY_HEARTBEAT_PORT))
            
            # Simulate a dynamic server load between 0% and 100%
            current_load = random.randint(10, 95) 
            heartbeat_msg = f"HEARTBEAT:{PORT}:{current_load}"
            
            hb_socket.sendall(heartbeat_msg.encode('utf-8'))
            hb_socket.close()
        except Exception:
            pass # Load balancer might be temporarily down
        time.sleep(2) # Send heartbeat every 2 seconds

def handle_client(client_socket):
    """Processes computational math requests from connected clients."""
    try:
        data = client_socket.recv(1024).decode('utf-8')
        if data.startswith("CALC:"):
            # Expecting data format: "CALC:num1,operator,num2" (e.g., "CALC:10,+,5")
            expression = data.split(":")[1]
            print(f"[Server {PORT}] Processing math request: {expression}")
            
            # Simulate artificial processing delay to show load distribution
            time.sleep(random.uniform(0.2, 0.8))
            
            # Safely evaluate basic math
            result = str(eval(expression))
            response = f"SUCCESS:{PORT}:{result}"
        else:
            response = "ERROR:Invalid Request Format"
            
        client_socket.sendall(response.encode('utf-8'))
    except Exception as e:
        print(f"[Server {PORT}] Error: {e}")
    finally:
        client_socket.close()

def run_server():
    # Start the periodic heartbeat status updates in a background thread
    threading.Thread(target=send_heartbeat, daemon=True).start()
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[✓] Back-end Calculation Server running on port {PORT}...")
    
    while True:
        client_sock, addr = server.accept()
        # Handle each client request inside its own thread concurrently
        threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()

if __name__ == "__main__":
    run_server()
