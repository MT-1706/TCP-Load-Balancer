import socket
import threading
import time
import sys

HOST = '0.0.0.0'
CLIENT_PORT = 7000      
HEARTBEAT_PORT = 5555
SERVER_IPS = {
    6001: '10.0.0.3', 
    6002: '10.0.0.4',
    6003: '10.0.0.5',
    6004: '10.0.0.6'
}

BALANCE_MODE = sys.argv[1] if len(sys.argv) > 1 else 'adaptive'
active_servers = {}
in_flight_requests = {}
lock = threading.Lock()
round_robin_counter = 0

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
                _, port_str, load_str = data.split(":")
                with lock:
                    active_servers[int(port_str)] = {"load": int(load_str), "last_seen": time.time()}
                    # Ensure logs write dynamically into our tracking file
                    print(f"[HEARTBEAT RECEIVED] HEARTBEAT:{port_str}:{load_str}", flush=True)
        except Exception as e:
            print(f"[Gateway] Heartbeat listener error: {e}", flush=True) 

def monitor_server_health():
    while True:
        time.sleep(1)
        now = time.time()
        with lock:
            to_remove = [p for p, info in active_servers.items() if now - info["last_seen"] > 8.0]
            for port in to_remove:
                print(f"[⚠️ SDN Controller Failure Alert] Node {port} dropped heartbeats.", flush=True)
                del active_servers[port]

def select_backend_server():
    global round_robin_counter

    with lock:
        server_ports = list(active_servers.keys())

        if not server_ports:
            return None, "No online back-end servers available"

        if BALANCE_MODE == 'static':
            port = server_ports[round_robin_counter % len(server_ports)]
            round_robin_counter += 1
            in_flight_requests[port] = in_flight_requests.get(port, 0) + 1
            return port, "Static Flow Assignment (Round-Robin)"

        underloaded = {
            p: info for p, info in active_servers.items()
            if info["load"] <= 80
        }

        candidates = underloaded if underloaded else active_servers

        best_port = min(
            candidates,
            key=lambda p: (
                candidates[p]["load"] + 10 * in_flight_requests.get(p, 0),
                in_flight_requests.get(p, 0)
            )
        )

        in_flight_requests[best_port] = (
            in_flight_requests.get(best_port, 0) + 1
        )

        if underloaded:
            reason = (
                f"Adaptive Routing (Reported Load: "
                f"{active_servers[best_port]['load']}%, "
                f"In-Flight: {in_flight_requests[best_port] - 1})"
            )
        else:
            reason = (
                f"Adaptive Emergency Flow (Load: "
                f"{active_servers[best_port]['load']}%, "
                f"In-Flight: {in_flight_requests[best_port] - 1})"
            )

        return best_port, reason

def handle_client_routing(client_socket):
    best_port = None
    backend_socket = None

    try:
        request = client_socket.recv(1024)

        if not request:
            return

        best_port, routing_log = select_backend_server()

        if best_port is None:
            client_socket.sendall(
                f"ERROR:{routing_log}".encode("utf-8")
            )
            return

        print(
            f"[{BALANCE_MODE.upper()} Flow Decision] "
            f"{routing_log} -> Route to {best_port}",
            flush=True
        )

        backend_socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        )
        backend_socket.settimeout(2.5)
        backend_socket.connect(
            (SERVER_IPS[best_port], best_port)
        )
        backend_socket.sendall(request)

        response = backend_socket.recv(1024)
        client_socket.sendall(response)

    except Exception as e:
        try:
            client_socket.sendall(
                f"ERROR:SDN Flow Interrupted ({e})".encode("utf-8")
            )
        except OSError:
            pass

    finally:
        if backend_socket is not None:
            backend_socket.close()

        if best_port is not None:
            with lock:
                in_flight_requests[best_port] = max(
                    0, in_flight_requests.get(best_port, 1) - 1
                )

        client_socket.close()

def run_gateway():
    threading.Thread(target=listen_for_heartbeats, daemon=True).start()
    threading.Thread(target=monitor_server_health, daemon=True).start()
    gateway_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    gateway_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    gateway_server.bind((HOST, CLIENT_PORT))
    gateway_server.listen(50)
    print(f"[✓] SDN Control Plane active on port {CLIENT_PORT} in {BALANCE_MODE.upper()} mode...", flush=True)
    while True:
        client_sock, _ = gateway_server.accept()
        threading.Thread(target=handle_client_routing, args=(client_sock,), daemon=True).start()

if __name__ == "__main__":
    run_gateway()
