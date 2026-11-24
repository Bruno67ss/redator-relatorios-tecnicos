# Auditoria para revisão local

A preparação inicial ocorreu em pasta independente, sem transportar histórico Git. Nesta etapa,
foi autorizada a criação de um histórico novo e o envio a um repositório privado. O projeto de
origem permanece somente leitura. A disponibilização pública não foi autorizada.

## Seleção e origem

Cada fonte selecionada foi lida e analisada antes da criação da cópia. Foram revisados o fluxo ativo,
prompts, imports, exemplos, testes, configuração e arquivos de dependências. Não foi usado um copiador
recursivo. Artefatos privados foram excluídos pela sua categoria e origem, sem transportar seu conteúdo.
O responsável confirmou autorização para envio privado do código reaproveitado. Essa confirmação
não equivale à escolha de licença nem à liberação para disponibilização pública.

- Reaproveitamento com adaptação: validação do cadastro, estado da sessão, verificação de identificadores,
  nomes de download, redação estruturada, checagem de evidência da queixa, revisão e conversão local.
- Reconstrução: identidade do aplicativo, exemplos, cenários técnicos, prompts principais, layout Word,
  documentação pública, configuração neutra e proteção de testes contra acesso externo.
- Exclusão: configurações preenchidas, credenciais, perfil privado, timbre, logos, templates binários,
  documentos emitidos, gravações, respostas reais de API, logs, backups, distribuições, modelos de voz,
  ambiente virtual anterior e histórico Git. Nenhum manual de fabricante foi incluído.
- Fluxos legados de organização intermediária e transcrição por modelos locais foram deixados de fora;
  não pertencem à interface atual. Os testes correspondentes não se aplicam à versão independente.

O inventário por arquivo está em [manifesto](MANIFESTO.json). Os cenários são fictícios de manutenção
de módulos eletrônicos e carregadores, sem transposição de laudos ou avaliações reais.

## Segurança

`scripts/audit_public.py` analisa as fontes e os nomes de arquivos de distribuição. Artefatos de execução
em `.venv/`, `local/` e caches são ignorados pelo Git e pela auditoria de fontes, e não podem ser enviados
em um pacote público. O script aceita termos proibidos por argumento e procura caminhos privados,
credenciais plausíveis e arquivos binários. Não substitui revisão humana de origem, contexto ou direitos.
Hashes das fontes de distribuição são guardados após a revisão para permitir detectar alterações.

## Validação e pendências

Os [resultados da validação](VALIDACAO.md) integram a documentação. O registro detalhado fica em
`local/validacao.json`, fora do versionamento.
Chamadas externas são bloqueadas na suíte; os testes de SDK usam transporte HTTP em memória.
O teste da aplicação cobre cadastro, geração local, revisão, invalidação da aprovação e DOCX.
O PDF real requer validação com o Word; um teste simulado verifica o comportamento da interface.

Antes de publicar: revisar este conjunto de fontes, confirmar titularidade, definir licença, conferir
dependências e imagens/documentos de demonstração. A demonstração com IA real e o acesso aos modelos
permanecem uma validação separada, com conteúdo fictício e eventual cobrança, ainda não executada.
O envio privado foi autorizado nesta etapa. Manter a visibilidade privada até a revisão específica
dos direitos e materiais destinados à disponibilização pública.
