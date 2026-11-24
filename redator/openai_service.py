"""Cliente comum e mensagens de erro sem conteúdo da requisição ou credenciais."""
from openai import OpenAI, APIConnectionError, APITimeoutError, APIStatusError


def create_client(api_key: str, *, http_client=None):
    options = {"http_client": http_client} if http_client is not None else {}
    # Duas novas tentativas com a espera progressiva do SDK para falhas transitórias.
    # O modelo permanece o escolhido pelo profissional, sem troca automática.
    return OpenAI(api_key=api_key, base_url="https://api.openai.com/v1",
                  timeout=60, max_retries=2, **options)


def error_message(exc: Exception) -> str:
    if isinstance(exc, APITimeoutError):
        message = "A OpenAI demorou além do limite para responder. Aguarde um pouco e tente novamente."
    elif isinstance(exc, APIConnectionError):
        message = "Não foi possível conectar à OpenAI. Confira a conexão com a internet e tente novamente."
    elif isinstance(exc, APIStatusError):
        status = exc.status_code
        if status == 503:
            message = "A OpenAI está temporariamente indisponível (503). Aguarde um pouco e tente novamente. Não é necessário alterar a chave por causa desse erro."
        elif status >= 500:
            message = f"A OpenAI apresentou uma falha temporária ({status}). Aguarde um pouco e tente novamente."
        elif status == 401:
            message = "A OpenAI recusou a autenticação (401). Confira a chave configurada no computador."
        elif status == 403:
            message = "A OpenAI negou acesso a esta solicitação (403). Confira as permissões do projeto e do modelo."
        elif status == 404:
            message = "O modelo ou recurso solicitado não está disponível para esta configuração (404). Confira o modelo na lateral."
        elif status == 429:
            if getattr(exc, "code", None) in {"insufficient_quota", "billing_hard_limit_reached", "organization_spend_limit_exceeded", "project_spend_limit_exceeded", "organization_usage_limit_exceeded"}:
                message = "A conta da API atingiu um limite de saldo ou de uso (429). Confira os créditos e limites do projeto OpenAI."
            else:
                message = "A OpenAI limitou temporariamente as solicitações (429). Aguarde um pouco antes de tentar novamente."
        else:
            message = f"A OpenAI recusou a solicitação ({status}). É necessário conferir a integração; alterar o ditado pode não resolver."
    else:
        message = "Ocorreu uma falha interna no aplicativo ao preparar o texto. Tente novamente; se persistir, precisamos conferir o aplicativo."
    # Nunca incluir str(exc), response, body, headers ou o pedido neste retorno.
    return message + " O texto da sua avaliação foi preservado."
