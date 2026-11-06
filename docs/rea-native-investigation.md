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

## Comparação dos logs: destinos diferentes (2026-11-06)

A investigação seguinte encontrou uma divergência concreta entre o teste do portal
no Windows e a conexão nativa no Mac, separados por cerca de 11 segundos:

| Origem | ID solicitado | Horário UTC | Resultado |
| --- | --- | --- | --- |
| Windows/portal | `604629388` | 15:01:14 | Cliente informado como offline |
| Mac/nativo | `604619388` | 15:01:25 | Rede estabelecida; sessão autorizada e iniciada às 15:01:27 |
| Windows/portal | `604629388` | 15:02:22 | Cliente informado como offline novamente |

O quinto dígito difere: `2` no Windows e `1` no Mac. O log do serviço Windows
confirma que recebeu exatamente o ID fornecido ao portal. O log do Mac confirma
`Net connection established`, `Session granted` e `Session started` para o outro
ID. Assim, os testes anteriores não comparavam o mesmo destino. A conclusão
anterior de causa desconhecida permanece válida para a indisponibilidade do ID
`604629388` em si, mas a discrepância entre a conexão que funcionou no Mac e a
que falhou no portal tem agora uma explicação documentada: IDs distintos.

Para comparar os clientes, o teste no portal deve usar o destino pretendido
confirmado pelo usuário; o ID com sessão bem-sucedida no Mac foi `604619388`.
Não houve nova solicitação de conexão nesta investigação nem substituição
automática do ID. Os registros históricos não garantem disponibilidade atual.

O serviço Windows permanecia em execução e com conexão TCP estabelecida ao
relay durante a inspeção. Também existem falhas de resolução de
`crl.anydesk.com`, mas não foi demonstrada relação causal com esse aviso offline.
Resumo sanitizado: `verification/offline-id-comparison.json`. Nenhum código da
ponte, configuração de rede ou binário AnyDesk foi alterado nesta etapa.

## Rastreamento do prazo de sessão (2026-11-06)

A investigação é somente de leitura: nenhuma alteração no executável instalado,
na licença ou nos arquivos de configuração. O novo artefato inclui regiões de
código escolhidas pelas referências aos parâmetros de tempo. Sua proveniência
está em `verification/rea-session-time-provenance.json`; pseudocódigo integral
permanece fora do Git. Endereços abaixo pertencem à base capturada, não são
endereços estáveis para outra versão ou execução.

O REA/Ghidra confirmou quatro referências a `ad.license.info.session_timeout`,
três à chave de contagem regressiva e duas ao texto de aviso de prazo próximo.
A leitura das funções recuperadas permite distinguir:

| Função atribuída pelo analisador | Evidência e interpretação |
| --- | --- |
| `FUN_0122aa90` | Consulta o parâmetro de prazo e faz uma conversão numérica. |
| `FUN_0122ab10` | Consulta separadamente o parâmetro da contagem regressiva. |
| `FUN_011d9040` | Compara uma duração calculada com um valor obtido pelo caminho de relógio; no ramo excedido atualiza estado/motivo e chama `FUN_011d74a0`. Também atualiza o aviso em outro caminho. |
| `FUN_011d74a0` | Encaminha uma ação associada a `FUN_011d5260`, diretamente ou pela fila da thread correspondente. |
| `FUN_00f46840` | Escolhe textos de aviso e utiliza o marcador `TIME_LEFT`; é um caminho de apresentação separado. |
| `FUN_0122c310` / `FUN_0122b2b0` | Consultam e convertem valores de propriedades com sincronização. A segunda trata especialmente as chaves de prazo, mas a origem final do valor efetivo não está demonstrada. |
| `FUN_01182e60` | Inclui as chaves de prazo entre várias propriedades de licença. A presença nessa estrutura não prova uma resposta de servidor. |

Os logs independentes mostram duas sessões interrompidas aproximadamente cinco
minutos depois de iniciadas: 300,901 e 300,083 segundos até `Stopping session`.
Em ambas, o encerramento e o fechamento do IPC precedem o diálogo de limitação
de licença. Isso separa o efeito visual do término da sessão.

Não foram encontradas as duas chaves de prazo persistidas nos arquivos verificados
`ProgramData/AnyDesk/{service,system}.conf` e
`Users/ti-it/AppData/Roaming/AnyDesk/{user,system}.conf`. Essa busca é limitada a
esses arquivos; não demonstra que o valor inexista em memória ou em outro local.

**Conclusão sustentada:** existe lógica no cliente relacionada ao prazo, separada
do texto do aviso. **Ainda não demonstrado:** quem fornece o prazo efetivo, se a
rede impõe um limite adicional, e se uma mudança local manteria a sessão. Não foi
feito teste de remoção de limite. As referências e identificadores de evidência
estão em `verification/rea-session-time-findings.json`.

Seguimento confirmado: `FUN_011d5260` altera um estado interno e encaminha outra
ação associada a `FUN_011d4f60`, ou chama uma operação virtual conforme o estado
atual. Esse último destino e as chamadas indiretas ainda não foram resolvidos.
Portanto, a cadeia foi rastreada até a transição de estado/encaminhamento; não
se declara um rastreamento completo até o fechamento final do transporte.
As sessões REA abertas nesta etapa foram fechadas normalmente.
