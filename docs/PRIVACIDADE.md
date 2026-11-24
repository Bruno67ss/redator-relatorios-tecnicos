# Dados e processamento

O cadastro de solicitante, setor, cidade, responsável, modelo e série é usado localmente para o
documento e o nome do download. Não é serializado para o provedor de redação. Tipo, lado, referências
naturais e avaliação técnica são enviados quando OpenAI é selecionada. A ajuda opcional também envia
as respostas técnicas. O endpoint é fixo em `https://api.openai.com/v1`.

A checagem local procura identificadores cadastrados e alguns padrões de contato. Ela não é uma
garantia de anonimização, não identifica todos os nomes e não prova que um relato pode ser divulgado.
A revisão humana do texto livre é obrigatória antes de enviar informações ao provedor.

Na transcrição, o áudio original é enviado sem recodificação, com nome genérico. A checagem de texto
ocorre depois da transcrição e não protege a voz nem identificadores já falados. Use somente fala
sintética ou uma gravação própria com conteúdo inteiramente fictício na demonstração.

Não há banco de dados ou gravação automática do áudio. Perfil, modelo neutro e arquivos de validação
podem existir em `local/`, ignorado pelo Git. Downloads ficam na pasta escolhida no navegador.
O conteúdo pode permanecer na memória da sessão até seu encerramento. Não use em computador compartilhado
com informações confidenciais sem controles adicionais. Não habilite logs de depuração do SDK.

`store=False` é enviado à API de redação; não é enviado à transcrição e não significa ausência de retenção
pelo provedor. Os termos e configurações da conta precisam ser avaliados antes de qualquer uso real.
