"""Impede uso acidental de credenciais e de rede externa durante toda a suíte."""
import ipaddress
import socket
import dotenv
import pytest

@pytest.fixture(autouse=True)
def offline_environment(monkeypatch):
    # O app usa override=True: não permita recarregar credenciais reais do .env.
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("RELATORIO_TEMPLATE", "")
    monkeypatch.setenv("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    def allowed(address):
        if not isinstance(address, tuple):
            raise AssertionError("Conexão não permitida na suíte offline")
        try:
            return ipaddress.ip_address(address[0]).is_loopback
        except ValueError:
            return address[0] == "localhost"
    def connect(sock, address):
        assert allowed(address), "Rede externa bloqueada na suíte offline"
        return original_connect(sock, address)
    def connect_ex(sock, address):
        assert allowed(address), "Rede externa bloqueada na suíte offline"
        return original_connect_ex(sock, address)
    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
