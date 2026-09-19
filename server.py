import socket
import threading


HOST = "0.0.0.0"
PORT = 8080

clients = []
clients_lock = threading.Lock()


def broadcast(data, exclude_socket=None):
    with clients_lock:
        current_clients = clients.copy()

    for client in current_clients:
        if client != exclude_socket:
            try:
                client.sendall(data)
            except:
                remove_client(client)


def remove_client(client_socket):
    with clients_lock:
        if client_socket in clients:
            clients.remove(client_socket)

    try:
        client_socket.close()
    except:
        pass


def handle_client(client_socket):
    buffer = b""

    while True:
        try:
            data = client_socket.recv(65536)

            if not data:
                break

            buffer += data

            # Одне повідомлення = один рядок JSON
            while b"\n" in buffer:
                message, buffer = buffer.split(b"\n", 1)

                if message:
                    broadcast(
                        message + b"\n",
                        exclude_socket=client_socket
                    )

        except:
            break

    remove_client(client_socket)

    print("Клієнт відключився")


def main():
    server_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server_socket.bind(
        (HOST, PORT)
    )

    server_socket.listen(20)

    print(
        f"Сервер запущено на "
        f"{HOST}:{PORT}"
    )

    while True:
        client_socket, addr = server_socket.accept()

        print(
            f"Підключився клієнт: {addr}"
        )

        with clients_lock:
            clients.append(client_socket)

        thread = threading.Thread(
            target=handle_client,
            args=(client_socket,),
            daemon=True
        )

        thread.start()


if __name__ == "__main__":
    main()