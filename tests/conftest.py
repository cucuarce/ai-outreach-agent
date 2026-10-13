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


@pytest.fixture(autouse=True)
def directorio_de_trabajo_temporal(tmp_path, monkeypatch):
    """Cada test corre en una carpeta temporal: los registros (`runs/` por defecto) no se
    escriben en el repositorio."""
    monkeypatch.chdir(tmp_path)
