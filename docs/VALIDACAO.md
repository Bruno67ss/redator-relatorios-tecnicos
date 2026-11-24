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

## Cidade e responsável editáveis

Melhoria validada em 24/11/2026: **153 testes aprovados**, com rede externa bloqueada e sem
chamadas reais à API. A suíte também impede que o aplicativo recarregue credenciais do `.env`.
Os testes cobrem valores iniciais do perfil, edição apenas na sessão, data automática, exemplo
fictício, inserção da identificação no DOCX e encaminhamento desse mesmo DOCX ao conversor PDF.
Alterar cidade ou responsável após geração, aprovação ou exportação remove o resultado anterior
e exige nova geração e aprovação, nos formatos Objetivo e Detalhado.

Requisições simuladas de redação e ajuda técnica confirmam que cidade e responsável não integram
o conteúdo enviado à IA. A proteção local também bloqueia a cidade cadastrada quando inserida
no relato ou nos esclarecimentos; a proteção existente do responsável foi preservada.

Uma exportação real pela interface produziu DOCX e PDF com identificação fictícia editada,
usando o Word instalado. O texto do PDF foi conferido e sua única página foi renderizada e
revisada visualmente, sem cortes ou sobreposições. Os artefatos ficam em
`local/validacao-identificacao/`, fora do versionamento.

A auditoria adicional das fontes apontou somente o `.env` local preexistente como arquivo
indevido para distribuição. Ele não é versionado e não foi alterado; deve continuar fora de
qualquer pacote de publicação. Não houve alteração de dependências, commit, push ou publicação.

Permanecem para revisão antes de publicar: titularidade do código reaproveitado, escolha da licença,
obrigações das dependências e das bibliotecas nativas, e todo material de demonstração destinado à
divulgação. O responsável autorizou explicitamente o envio privado nesta etapa. Isso não autoriza alterar a visibilidade para pública.
