
import socket
import threading
import time

GATEWAY_HOST = '10.0.0.2'
GATEWAY_PORT = 7000
NUM_REQUESTS = 10

latencies = []
successful_requests = 0
failed_requests = 0
lock = threading.Lock()


def send_calculation_task(client_id, expression):
    global successful_requests, failed_requests

    start = time.perf_counter()
    client = None

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5)
        client.connect((GATEWAY_HOST, GATEWAY_PORT))
        client.sendall(f"CALC:{expression}".encode('utf-8'))

        response = client.recv(1024).decode('utf-8').strip()
        duration = (time.perf_counter() - start) * 1000

        with lock:
            latencies.append(duration)

            if response.startswith("SUCCESS:"):
                successful_requests += 1
                print(
                    f"[Client #{client_id}] SUCCESS: "
                    f"{expression} -> {response} ({duration:.2f} ms)"
                )
            else:
                failed_requests += 1
                print(
                    f"[Client #{client_id}] FAILED: "
                    f"{expression} -> {response} ({duration:.2f} ms)"
                )

    except Exception as e:
        with lock:
            failed_requests += 1
        print(f"[Client #{client_id}] ERROR: {e}")

    finally:
        if client is not None:
            client.close()


def run_simulation():
    global successful_requests, failed_requests

    latencies.clear()
    successful_requests = 0
    failed_requests = 0

    math_tasks = [
        "45*12",
        "1024+512",
        "89-43",
        "400/8",
        "7*8",
        "123+456",
        "999-111",
        "50*50",
        "12/4",
        "88+12"
    ]

    start_sim = time.perf_counter()

    threads = [
        threading.Thread(
            target=send_calculation_task,
            args=(i + 1, expression)
        )
        for i, expression in enumerate(math_tasks)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    total_duration = time.perf_counter() - start_sim
    avg_latency = (
        sum(latencies) / len(latencies)
        if latencies else 0
    )

    throughput = (
        successful_requests / total_duration
        if total_duration > 0 else 0
    )

    print("\n" + "=" * 48)
    print("       PERFORMANCE METRICS SUMMARY")
    print("=" * 48)
    print(f"Total requests          : {NUM_REQUESTS}")
    print(f"Successful requests     : {successful_requests}")
    print(f"Failed requests         : {failed_requests}")
    print(f"Total workload time     : {total_duration * 1000:.2f} ms")
    print(f"Average response latency: {avg_latency:.2f} ms")
    print(f"Throughput              : {throughput:.2f} requests/second")
    print("=" * 48)


if __name__ == "__main__":
    run_simulation()
