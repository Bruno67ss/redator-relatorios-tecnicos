"""Dados criados para demonstração; sem origem em atendimento ou documento real."""
from datetime import date
from .domain import Case, Identity, TechnicalItem

def demo_case() -> Case:
    return Case("Solicitante Exemplo", "Setor Demonstração", "Cidade Exemplo", date(2026, 1, 15),
                "Responsável Exemplo", (
                    Identity("E1", "Módulo eletrônico", "Direito", "Modelo Fictício A", "DEMO-001"),
                    Identity("E2", "Carregador", "", "Modelo Fictício B", "DEMO-002"),
                ), (
                    TechnicalItem("E1", "Falha intermitente de carga e poeira nos contatos.",
                                  "Realizadas limpeza dos contatos e avaliação funcional em bancada.",
                                  "O funcionamento foi restabelecido durante o teste; a durabilidade permanece incerta.",
                                  "Funcionamento restabelecido no teste. Recomenda-se acompanhamento, sem garantia de durabilidade."),
                    TechnicalItem("E2", "Indicador luminoso apagado durante a tentativa de carregamento.",
                                  "Realizado teste com fonte compatível e verificação dos contatos. Não foi executada substituição.",
                                  "A falha persistiu nos testes realizados.",
                                  "Indica-se a substituição do carregador, ainda não realizada."),
                ))
