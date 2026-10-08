import socket

import pytest


def test_create_connection_esta_bloqueado():
    with pytest.raises(RuntimeError, match="red bloqueada"):
        socket.create_connection(("example.com", 80), timeout=1)


def test_socket_connect_esta_bloqueado():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(RuntimeError, match="red bloqueada"):
            s.connect(("127.0.0.1", 11434))
    finally:
        s.close()
