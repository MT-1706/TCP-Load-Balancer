import socket
import threading
import time

GATEWAY_HOST = '10.0.0.2'
GATEWAY_PORT = 7000

latencies = []
lock = threading.Lock()

def send_calculation_task(client_id, expression):
    start = time.time()
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((GATEWAY_HOST, GATEWAY_PORT))
        client.sendall(f"CALC:{expression}".encode('utf-8'))
        response = client.recv(1024).decode('utf-8')
        duration = (time.time() - start) * 1000 # Milliseconds
       
        with lock:
            latencies.append(duration)
        print(f"[Client #{client_id}] Complete: {expression} -> {response} ({duration:.1f}ms)")
        client.close()
    except Exception as e:
        print(f"[Client #{client_id}] Connection Timeout Drop: {e}")

def run_simulation():
    global latencies
    latencies = []
    math_tasks = ["45*12", "1024+512", "89-43", "400/8", "7*8", "123+456", "999-111", "50*50", "12/4", "88+12"]
   
    start_sim = time.time()
    threads = [threading.Thread(target=send_calculation_task, args=(i+1, expr)) for i, expr in enumerate(math_tasks)]
   
    for t in threads: t.start()
    for t in threads: t.join()
   
    total_duration = (time.time() - start_sim) * 1000
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
   
    print("\n" + "="*45)
    print(f"📊 PERFORMANCE METRICS RESULTS SUMMARY")
    print("="*45)
    print(f" Total Workload Evaluation Time: {total_duration:.2f} ms")
    print(f" Average Response Pipeline Latency: {avg_latency:.2f} ms")
    print(f" Successful Packets Transmitted: {len(latencies)}/10")
    print("="*45 + "\n")

if __name__ == "__main__":
    run_simulation()
