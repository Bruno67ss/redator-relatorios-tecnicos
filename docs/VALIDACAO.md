# Validação da versão independente

Verificação concluída em 24/11/2026, com dados inteiramente sintéticos.

| Verificação | Resultado |
| --- | --- |
| Instalação independente | Ambiente Python 3.12 criado do zero; sem copiar o ambiente anterior |
| Suíte aplicável | 139 testes aprovados, sem falhas |
| Chamadas reais à OpenAI | Nenhuma; respostas simuladas, HTTP em memória e rede externa bloqueada na suíte |
| Dependências | pip check sem incompatibilidades; 56 distribuições inventariadas localmente |
| Interface | Cadastro, geração local, revisão, invalidação da aprovação e preparação de documentos exercitados |
| Servidor real | Health e página HTTP 200 em loopback; processo de teste encerrado |
| DOCX real | Gerado com conteúdo sintético, modelo neutro e autor vazio |
| PDF real | Convertido localmente pelo Microsoft Word; uma página, autor vazio |
| Revisão visual | PDF renderizado e conferido, sem cortes ou sobreposições |
| Fontes públicas | Auditoria de nomes privados, caminhos, credenciais e arquivos indevidos sem achados |
| Projeto de origem | 250 hashes SHA-256 preservados, sem adições; estado Git limpo |
| Histórico e publicação | Histórico novo autorizado; envio apenas privado; nenhuma disponibilização pública |

A checagem de integridade exclui o ambiente virtual anterior, caches e metadados Git; o estado do
checkout foi verificado separadamente sem atualização do índice. Duas pastas antigas de validação
sem permissão de leitura foram excluídas e não copiadas. Não houve escrita no projeto de origem.

Os detalhes de execução, inventário de dependências, hashes e documentos sintéticos estão em
local/, fora do versionamento. Esses artefatos e o novo ambiente virtual não integram as fontes
públicas. A lista por arquivo está no [manifesto](MANIFESTO.json).

Os fluxos legados retirados não foram testados, pois não existem nesta versão. O teste de transcrição
cobre requisições e respostas simuladas e os formatos de áudio; não confirma a disponibilidade real
dos modelos ou a qualidade de reconhecimento de fala. A redação real pela IA também não foi chamada.
Somente Windows foi validado nesta etapa.

Permanecem para revisão antes de publicar: titularidade do código reaproveitado, escolha da licença,
obrigações das dependências e das bibliotecas nativas, e todo material de demonstração destinado à
divulgação. O responsável autorizou explicitamente o envio privado nesta etapa. Isso não autoriza alterar a visibilidade para pública.
