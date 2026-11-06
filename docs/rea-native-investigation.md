# Investigação nativa com REA — 2026-11-06

Objetivo: verificar se há uma interface de conexão reutilizável separada da
interface visual do AnyDesk, para orientar a evolução da ponte web na branch `dev`.

## Artefato e método

- AnyDesk Windows 9.0.12, PE32/x86, 5.635.000 bytes.
- SHA-256: `78c26bc768144343954bce16a074f19a366e747d8c44141538da6d7deda0e9f4`.
- REA 6.5.0 com Ghidra 12.1.4 e Java 21 já instalados no Windows.
- Análise estática de cópia em `.runtime/rea-2026-11-06/`; sem executar a
  cópia, modificar o cliente instalado ou anexar debugger à sessão em uso.
- Java/Ghidra configurados apenas no ambiente do comando de análise.
- Evidências completas locais: `overview.json`, `entry.json`, `pe-layout.json`.
  O executável e os arquivos de trabalho permanecem fora do Git.

## Observações

O REA/Ghidra concluiu a análise padrão e reportou 53 procedimentos e 25 strings
definidas. Esses números descrevem o que o analisador reconheceu, não a totalidade
da implementação do AnyDesk.

A leitura independente dos cabeçalhos PE encontrou:

| Região | Tamanho virtual | Bytes no arquivo |
| --- | ---: | ---: |
| `.text` | 10.359 | 10.752 |
| `.itext` | 18.688.512 | 0 |
| `.data` | 5.582.180 | 5.581.312 |

A seção `.data` tem entropia aproximada de 7,99996 bits/byte. A entrada é
`0x403653` (base `0x400000`, RVA `0x3653`), e o diretório PE de importações
convencional tem RVA e tamanho zero.

O REA recuperou pseudocódigo da entrada. Ela chama rotinas em `0x401707`,
`0x401612`, `0x401456`, `0x4013fd` e `0x40362d`, usa ponteiros de função e
retorna códigos de falha 1000/1001. Os nomes `FUN_*` são atribuídos pelo
analisador; não são nomes do código-fonte original.

## Interpretação e limites

A região virtual extensa sem bytes no arquivo, a alta entropia dos dados e a
pequena quantidade de código reconhecido são indícios fortes de empacotamento
ou compressão. Ainda não identificamos o formato do empacotador, a rotina de
conexão ou o desenho do aviso de sessão não comercial.

Não foi demonstrada uma API utilizável para extrair somente a conexão. A análise
da entrada não equivale à recuperação do programa inteiro, e uma busca vazia
por strings não provaria a ausência da funcionalidade.

Próximo passo técnico: acompanhar a inicialização até identificar como o código
principal é materializado e obter uma representação analisável dele, preservando
a identidade separada de qualquer artefato derivado. Só então mapear conexão,
renderização e seus limites. A possibilidade de um cliente independente
compatível com IDs AnyDesk permanece não demonstrada.

Esta investigação não altera a ponte web nem explica, por si só, o encerramento
ocasional das sessões. O teste de teclado/mouse remoto de ponta a ponta continua
pendente de um destino online.

## Segunda etapa: código carregado (2026-11-06)

Para avançar além do carregador, foi feita leitura somente das páginas executáveis
ou somente de leitura das regiões `.text` e `.itext` do módulo AnyDesk já em
execução. Não houve debugger, suspensão do processo, alteração do binário instalado
ou cópia de heaps/stacks. Páginas graváveis sem permissão de execução foram
omitidas e representadas por zeros, com os intervalos registrados na proveniência.

A região `.itext` contém outro cabeçalho PE válido. A partir dele foi reconstruído
um artefato **somente para análise**, com cinco seções e aproximadamente 9 MB de
código `.text`. Ele não é um executável recuperado completo e não deve ser
executado: dados graváveis estão incompletos e importações/chamadas indiretas
podem não ser recuperáveis. Endereços observados incluem a base do processo
na captura; não são endereços universais para outra execução.

- Origem instalada: SHA-256 `78c26bc768144343954bce16a074f19a366e747d8c44141538da6d7deda0e9f4`.
- PE interno reconstruído: SHA-256 `c9e8abc06345d32864f6b80ee47d64a09804b18d1e2bf43c0337449a564c9667`.
- Base observada do PE interno: `0xeb4000`.
- As cópias binárias permanecem em `.runtime/rea-2026-11-06/`, fora do Git.

A inspeção de bytes encontrou as chaves de interface
`ad.dlg.closed.client_offline.message` e `ad.dlg.closed.client_offline.title`.
Para a chave da mensagem, em `0x1dce3b8`, há três candidatos a referências por
ponteiro: `0xff1f05`, `0xff20b5` e `0x11088e3`. Esses locais foram encontrados
por comparação de bytes, não por confirmação de fluxo de execução. Os bytes
imediatamente anteriores incluem o opcode x86 `push`; o REA deve confirmar
as funções que os contêm e suas referências analisadas.

O REA/Ghidra foi direcionado ao PE interno reconstruído para obter visão geral,
referências e pseudocódigo das funções candidatas numa única sessão. Isso não
significa que a causa do destino offline foi determinada nem que já existe uma
API de conexão separável. Os logs da tentativa conhecida mostram que o AnyDesk
recebeu o ID solicitado, consultou informações do cliente e informou que ele
parecia offline; a análise estática não prova a disponibilidade atual do destino.

## Resultado do REA: caminho do aviso offline

A análise do PE interno completo atingiu o timeout do provedor após 600.000 ms.
Para limitar o trabalho, um segundo artefato manteve três regiões de código
(`0xfe8000–0x1000000`, `0x1100000–0x1110000` e `0x16e0000–0x16f0000`,
finais exclusivos) e os dados somente de leitura. Os demais endereços de código
ficaram ausentes; as omissões de dados graváveis anteriores continuam válidas.

Nesse recorte, o REA/Ghidra concluiu a análise e reconheceu 1.251 procedimentos
e 13.317 strings. Esses números pertencem ao recorte, não ao programa completo.
Confirmou três referências à chave da mensagem offline nas instruções
`0xff1f04`, `0xff20b4` e `0x11088e2`. Os endereços da etapa anterior apontavam
para o operando imediato, um byte depois do início dessas instruções.

As referências pertencem a duas funções com pseudocódigo recuperado:

- `FUN_00ff1b90`: em um dos caminhos, seleciona o título offline quando
  `param_4 == 0x0c`. O contexto importa: outro caminho com esse mesmo valor
  seleciona o título de limite de tentativas. Portanto, não foi demonstrado
  que `0x0c` seja um código universal de erro de rede ou do protocolo.
- `FUN_01108880`: usa as chaves de título e mensagem offline na construção
  do diálogo. Isso localiza o tratamento visual do estado, não sua origem.

Os nomes são gerados pelo analisador. Tipos, convenções de chamada e destinos
indiretos podem estar incompletos. A sessão de análise foi encerrada; o binário
instalado e o código da ponte web não foram modificados nesta etapa.

A proveniência está em `verification/rea-offline-regions-provenance.json` e o
resumo com identificadores de evidência em `verification/rea-offline-findings.json`.
Binários e pseudocódigo integral permanecem somente em `.runtime/`, fora do Git.

O próximo ponto de investigação é quem produz o estado recebido por esse
tratador de interface. Ainda não sabemos por que o destino `604629388` foi
considerado offline, nem demonstramos conexão independente do cliente nativo.
