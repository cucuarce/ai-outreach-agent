"""Configuración común de la suite.

Ningún test puede abrir conexiones de red (principio V de la constitución, research R10).
Moto intercepta boto3 en proceso, sin sockets, así que es compatible con este bloqueo.
"""

import socket

import pytest


def _red_bloqueada(*args, **kwargs):
    raise RuntimeError("red bloqueada en tests")


@pytest.fixture(autouse=True)
def bloquear_red(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _red_bloqueada)
    monkeypatch.setattr(socket.socket, "connect_ex", _red_bloqueada)
    monkeypatch.setattr(socket, "create_connection", _red_bloqueada)
