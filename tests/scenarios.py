"""Cenários inventados para uma bancada fictícia de módulos eletrônicos."""
from datetime import date
from redator.domain import Case, Identity, TechnicalItem

LEFT = ("O módulo esquerdo chegou com queixa de falha intermitente de carga. "
        "Observamos poeira no conector. Realizamos limpeza a seco e teste de carga. "
        "O funcionamento foi restabelecido durante o teste; não confirmamos a durabilidade. "
        "Recomendamos acompanhamento.")
RIGHT = ("O módulo direito não iniciou a carga durante o teste de bancada. "
         "Foi testado outro cabo compatível, sem sucesso. "
         "A causa não foi confirmada. Recomendamos avaliação complementar, ainda não realizada.")
CHARGER = ("O carregador apresentava poeira na carcaça. Realizamos limpeza externa. "
           "Em seguida o funcionamento ficou dentro dos padrões no teste relatado.")

def three_device_case():
    identities = (Identity("E1", "Módulo eletrônico", "Esquerdo", "Fictício A", "SINT-001"),
                  Identity("E2", "Módulo eletrônico", "Direito", "Fictício B", "SINT-002"),
                  Identity("E3", "Carregador", "", "Fictício C", "SINT-003"))
    return Case("Solicitante Simulado", "Setor Simulado", "Cidade Exemplo", date(2026, 1, 15),
                "Responsável Exemplo", identities, tuple(TechnicalItem(i.alias, "", "", "", "") for i in identities))

def combined_assessment():
    return LEFT + "\n\n" + RIGHT + "\n\n" + CHARGER

def three_device_response():
    return {"paragraphs": [
        "O módulo esquerdo apresentava poeira no conector. Realizamos limpeza a seco e teste de carga, restabelecendo o funcionamento durante o teste. A durabilidade não foi confirmada; recomendamos acompanhamento.",
        "O módulo direito não iniciou a carga. O teste com outro cabo compatível não teve sucesso. A causa não foi confirmada; recomendamos avaliação complementar, ainda não realizada.",
        "Realizamos limpeza externa do carregador; o funcionamento ficou dentro dos padrões no teste relatado."],
        "complaints": [{"alias": "E1", "text": "falha intermitente de carga", "source_quote": "falha intermitente de carga"}], "notes": []}

def shared_charging_assessment():
    return ("Recebemos o módulo eletrônico direito, o módulo eletrônico esquerdo e o carregador "
            "com queixa de falha no carregamento de ambos os módulos. "
            "Os dois módulos carregaram usando outra fonte compatível. "
            "O carregador original apresentou falha no teste. Recomendamos substituir o carregador. "
            "A substituição ainda não foi realizada.")

def shared_charging_response():
    return {"paragraphs": [
        "Os dois módulos carregaram usando outra fonte compatível.",
        "O carregador original apresentou falha no teste.",
        "Recomendamos substituir o carregador. A substituição ainda não foi realizada."],
        "complaints": [{"alias": alias, "text": "falha no carregamento",
                        "source_quote": "falha no carregamento de ambos os módulos"} for alias in ("E1", "E2")],
        "notes": []}
