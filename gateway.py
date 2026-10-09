import socket
import threading
import time
import sys

HOST = '0.0.0.0'
CLIENT_PORT = 7000      
HEARTBEAT_PORT = 5555
SERVER_IPS = {6001: '10.0.0.3', 6002: '10.0.0.4'}

# Set mode from terminal command line argument: 'adaptive' or 'static'
BALANCE_MODE = sys.argv[1] if len(sys.argv) > 1 else 'adaptive'

active_servers = {}
lock = threading.Lock()
round_robin_counter = 0

# Metrics collection counters
total_requests = 0
total_routing_time = 0

def listen_for_heartbeats():
    hb_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    hb_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    hb_server.bind((HOST, HEARTBEAT_PORT))
    hb_server.listen(10)
    while True:
        try:
            conn, _ = hb_server.accept()
            data = conn.recv(1024).decode('utf-8')
            conn.close()
            if data.startswith("HEARTBEAT:"):
                print(f"[HEARTBEAT RECEIVED] {data}", flush=True)
                _, port_str, load_str = data.split(":")
                with lock:
                    active_servers[int(port_str)] = {"load": int(load_str), "last_seen": time.time()}
        except Exception: pass

def monitor_server_health():
    while True:
        time.sleep(1)
        now = time.time()
        with lock:
            to_remove = [p for p, info in active_servers.items() if now - info["last_seen"] > 4.0]
            for port in to_remove:
                print(f"[⚠️ SDN Controller Failure Alert] Node {port} dropped heartbeats. Removing flow entry.")
                del active_servers[port]

def select_backend_server():
    global round_robin_counter
    with lock:
        server_ports = list(active_servers.keys())
        if not server_ports:
            return None, "No online back-end servers available"
       
        # --- MODE 1: STATIC LOAD BALANCING (Round-Robin) ---
        if BALANCE_MODE == 'static':
            port = server_ports[round_robin_counter % len(server_ports)]
            round_robin_counter += 1
            return port, f"Static Flow Assignment (Round-Robin)"
           
        # --- MODE 2: ADAPTIVE LOAD BALANCING (Least Load & Overload Avoidance) ---
        else:
            # Check for overloaded nodes (>80% load)
            underloaded = {p: info for p, info in active_servers.items() if info["load"] <= 80}
           
            if underloaded:
                best_port = min(underloaded, key=lambda k: underloaded[k]["load"])
                return best_port, f"Adaptive SDN Routing Decision (Least-Load: {underloaded[best_port]['load']}% Utilization)"
            else:
                # If everything is overloaded, pick absolute minimum to prevent catastrophic request timeout drops
                best_port = min(active_servers, key=lambda k: active_servers[k]["load"])
                print(f"[⚡ Network Load Alert] All servers overloaded! Directing flow dynamically to least impacted node.")
                return best_port, f"Adaptive Emergency Flow (Load: {active_servers[best_port]['load']}%)"

def handle_client_routing(client_socket):
    global total_requests, total_routing_time
    start_time = time.time()
    try:
        request = client_socket.recv(1024)
        best_port, routing_log = select_backend_server()
       
        if best_port is None:
            client_socket.sendall(f"ERROR:{routing_log}".encode('utf-8'))
            return

        print(f"[{BALANCE_MODE.upper()} Flow Decision] {routing_log} -> Route to {best_port}")
       
        backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        backend_socket.settimeout(2.5)
        backend_socket.connect((SERVER_IPS[best_port], best_port))
        backend_socket.sendall(request)
       
        response = backend_socket.recv(1024)
        backend_socket.close()
        client_socket.sendall(response)
       
        with lock:
            total_requests += 1
            total_routing_time += (time.time() - start_time)
           
    except Exception as e:
        client_socket.sendall(f"ERROR:SDN Flow Interrupted ({e})".encode('utf-8'))
    finally:
        client_socket.close()

def run_gateway():
    threading.Thread(target=listen_for_heartbeats, daemon=True).start()
    threading.Thread(target=monitor_server_health, daemon=True).start()
   
    gateway_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    gateway_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    gateway_server.bind((HOST, CLIENT_PORT))
    gateway_server.listen(50)
    print(f"[✓] SDN Control Plane running in **{BALANCE_MODE.upper()}** balancing mode on port {CLIENT_PORT}...")
   
    while True:
        client_sock, _ = gateway_server.accept()
        threading.Thread(target=handle_client_routing, args=(client_sock,), daemon=True).start()

if __name__ == "__main__":
    run_gateway()
