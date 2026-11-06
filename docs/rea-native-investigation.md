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
