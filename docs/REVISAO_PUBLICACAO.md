# Revisão para registro e envio privado

Revisão de 24/11/2026. O responsável confirmou autorização para enviar o código reaproveitado a
um novo repositório privado. Nenhuma licença de código aberto foi atribuída. A liberação pública
e a licença continuam sujeitas a uma decisão posterior.

## Fontes e dados

Foram revisados README, manifesto, validação, dependências, fontes, testes e exemplos. Os cenários
são sintéticos de manutenção de equipamentos. Não foram incluídos documentos de fabricantes,
templates institucionais, imagens, gravações ou dados de produção.

Somente as fontes relacionadas no manifesto e o arquivo vazio local/.gitkeep integram o registro.
Ambientes virtuais, configurações preenchidas, logs, áudios, documentos gerados, backups, modelos,
arquivos de credenciais e artefatos de compilação permanecem fora do Git.

## Ajustes da revisão

O identificador do formato estruturado da redação foi corrigido para usar somente ASCII, sem
alterar o texto visível, os prompts ou a lógica de redação. O contrato da API exige letras ASCII,
dígitos, hífen ou sublinhado, até 64 caracteres. O transporte HTTP simulado e o teste de requisição
agora verificam esse requisito, conforme a
[referência oficial](https://developers.openai.com/api/reference/resources/responses/methods/create).

O README foi ajustado para um visitante sem contexto anterior, para explicar corretamente o uso
de gravações próprias fictícias e para registrar o alcance da autorização recebida.

## Dependências e limites

O commit distribui código do projeto e especificações de dependências; não inclui código instalado
de terceiros, wheels, DLLs, fontes de fabricante ou o Microsoft Word. As licenças de terceiros
continuam próprias. Redistribuir bibliotecas nativas, codecs ou um instalador exigirá nova revisão,
conforme [dependências e titularidade](DEPENDENCIAS.md).

A suíte usa respostas simuladas e bloqueia conexões externas. Não foi feita chamada paga à OpenAI,
nem validada a disponibilidade real dos modelos nesta conta. Os resultados locais anteriores de
servidor, DOCX e PDF permanecem documentados em [validação](VALIDACAO.md).

O novo histórico parte de um único commit inicial na branch main. O projeto de origem não foi
modificado e seu histórico não foi copiado. O repositório remoto deve permanecer privado.
