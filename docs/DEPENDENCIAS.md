# Dependências, licenças e titularidade

Revisão em 24/11/2026. O responsável confirmou autorização para o envio do código reaproveitado
a um repositório privado. Não foi atribuída licença ao código próprio. A disponibilização pública,
a escolha da licença e os direitos necessários a essa modalidade permanecem sujeitos à revisão.
A ausência de identificadores não resolve direitos autorais, relações contratuais ou segredo empresarial.
Os prompts foram reescritos para manutenção genérica; não utilizam manuais ou base de conhecimento externa.

| Componente | Uso | Licença ou condição a conferir |
| --- | --- | --- |
| Streamlit | Interface local | Apache-2.0; [licença oficial](https://github.com/streamlit/streamlit/blob/develop/LICENSE) |
| SDK OpenAI | Cliente de redação e transcrição | Apache-2.0; [licença oficial](https://github.com/openai/openai-python/blob/main/LICENSE) |
| python-docx | Criação do DOCX | MIT; [licença oficial](https://github.com/python-openxml/python-docx/blob/master/LICENSE) |
| python-dotenv | Configuração local | BSD-3-Clause, conforme metadados instalados |
| PyAV | Inspeção de áudio | BSD-3-Clause no pacote; bibliotecas FFmpeg têm condições próprias |
| pywin32 | Automação do Word | PSF nos metadados instalados; preservar os avisos de terceiros aplicáveis |
| pytest | Testes | MIT, conforme metadados instalados |
| HTTPX | Transporte HTTP e testes simulados | BSD-3-Clause, conforme metadados instalados |
| Microsoft Word | PDF opcional no Windows | Software proprietário instalado e licenciado pelo usuário; não distribuído |
| API OpenAI | Serviço remoto opcional | Termos do serviço, acesso aos modelos e cobrança separados da licença do SDK |

Os wheels do PyAV incluem bibliotecas FFmpeg; a configuração do build e os codecs afetam as obrigações.
Confira a [instalação oficial](https://pyav.org/docs/stable/overview/installation.html) e o
[guia de licenças do FFmpeg](https://ffmpeg.org/legal.html) antes de redistribuir binários ou montar um instalador.
Esta entrega contém somente fontes e listas de dependências, sem wheels, modelos, DLLs ou instaladores.

Os arquivos lock preservam versões já usadas pela integração e recebem marcador de plataforma para
pywin32. Ferramentas legadas de reconhecimento local e a ferramenta de inspeção documental não foram
incluídas. Um inventário dos metadados instalados acompanha a validação local. Isso não substitui a
verificação de avisos de todas as dependências transitivas nem uma análise de vulnerabilidades atualizada.

Antes de disponibilizar publicamente: confirmar os direitos para essa modalidade, escolher a licença e revisar dependências transitivas,
validar os modelos na conta de demonstração e revisar qualquer captura ou documento que será divulgado.
