# AnyDesk pelo navegador usando TI-LOCAL como ponte

Status: aprovado pelo usuário em 05/11/2026; implementação local em `anydesk-web-bridge/`. Evidências e limitações atuais no README e PROGRESS.md desse projeto.

## Objetivo e decisões confirmadas

Marcos quer informar um ID AnyDesk no navegador, visualizar a sessão remota e controlar mouse e teclado. A conexão deve continuar compatível com o AnyDesk existente. Marcos escolheu usar o Windows TI-LOCAL, IP 10.0.2.141, como intermediário. Solicitou o uso do REA na investigação.

## Evidência disponível

- SSH funciona com a conta marcos. Não incluir credenciais no projeto.
- Windows 11 Pro, versão reportada 10.0.26200; Python 3.12 e Node disponíveis.
- AnyDesk instalado em `C:\Program Files (x86)\AnyDesk\AnyDesk.exe`, versão de arquivo 9.0.12.
- Sessão gráfica 1: usuário ti-it, RDP ativo, AnyDesk aberto. Sessão 2: marcos, desconectada. Estes IDs são observações, não constantes de implementação.
- REA 6.5.0 em `C:\Users\marcos\corte-ai\ferramentas\rea-runtime\node_modules\rea-agents`. A inspeção estática inicial identificou PE de 5.635.000 bytes, SHA-256 `78c26bc768144343954bce16a074f19a366e747d8c44141538da6d7deda0e9f4`. Não houve reconstrução do protocolo, decompilação completa nem prova de captura de vídeo.
- O arquivo `anydesk.dmg` mencionado pelo usuário não foi localizado nas buscas iniciais. O executável analisado foi o instalado no Windows, não um anexo identificado.
- A CLI oficial permite iniciar conexão por ID e oferece `--plain`: https://support.anydesk.com/docs/command-line-interface-for-windows . Isso não fornece um fluxo de vídeo web.
- A pasta de trabalho atual não é um repositório Git; o documento permanece como arquivo local, sem commit.

## Abordagens

1. **Ponte Windows, escolhida pelo usuário:** o AnyDesk original mantém a conexão e o protocolo. Um serviço nosso entrega interface, vídeo e entrada ao navegador. Depende de sessão gráfica utilizável e acrescenta latência.
2. **Cliente web independente, não escolhido:** reconstruir o protocolo e renderização usando investigação com REA. Compatibilidade não comprovada e escopo consideravelmente maior.

O REA apoia a identificação e investigação do aplicativo real. Não é um conversor automático de EXE/DMG para aplicação web.

## Proposta de primeira versão

- Interface em português: autenticação, campo de ID numérico, botão Conectar, área de vídeo, tela cheia, Desconectar e mensagens de erro reais.
- Uma conexão e um controlador por vez. Solicitações concorrentes não tomam controle da sessão existente.
- Aceitação da conexão pelo destinatário pela interface normal do AnyDesk. Inicialmente não criar nem alterar senhas de acesso não supervisionado.
- Mouse, clique, rolagem e teclado básico. Atalhos especiais, layouts e teclas de modificadores precisam de testes; Ctrl+Alt+Del, UAC/desktop seguro e telas bloqueadas não são prometidos.
- Exibir janela de espera, aceitação ou rejeição do próprio AnyDesk. O site distingue transporte de vídeo pronto de conexão remota aceita; não declara conexão AnyDesk bem-sucedida só porque iniciou o processo.
- Primeira entrega para validação local, com acesso pelo navegador via túnel SSH ao Windows. Publicação na internet e regras de firewall não fazem parte desta etapa proposta.
- Clipboard, áudio, transferência de arquivos, múltiplas sessões e reconexão após reiniciar o Windows ficam fora desta primeira versão.

## Arquitetura proposta pelo implementador

Navegador → serviço web autenticado no Windows → agente na sessão gráfica → janela do AnyDesk → computador remoto autorizado.

O serviço web oferece página e sinalização de vídeo. A proposta inicial é Python com aiohttp/aiortc, vídeo WebRTC e canal de controle autenticado. Bibliotecas e versões serão verificadas antes da implementação. Uma solução alternativa de transporte pode ser escolhida se a prova de captura mostrar impedimento, mantendo o escopo e informando a mudança.

Um agente na sessão gráfica inicia a conexão por ID usando argumentos de processo, sem shell e com validação estrita de ID. O agente captura apenas a janela do AnyDesk selecionada, através de uma API de captura por janela do Windows que seja validada com este aplicativo. Recortar uma captura do desktop inteiro não é equivalente: outras janelas poderiam aparecer. Não recorrer silenciosamente à transmissão do desktop completo.

A entrada só é aplicada quando a janela selecionada pertence ao processo esperado, está acessível e é a janela de destino apropriada. O mapeamento considera área útil, DPI, escala e limites. Perda de foco, minimização, desconexão do navegador e encerramento devem liberar teclas/botões e suspender a entrada. Nunca encaminhar teclas para um aplicativo diferente.

O serviço web e o agente usam IPC restrito às identidades locais necessárias. O navegador não recebe uma interface para executar comandos arbitrários.

## Sessão gráfica: dependência importante

A proposta é utilizar inicialmente a sessão ativa `ti-it`, capturando somente a janela do AnyDesk. Isso será visível nessa sessão e poderá disputar mouse e foco com quem estiver usando o Windows. A aprovação deste documento deve incluir essa escolha; é possível escolher outra sessão/máquina antes da implementação.

SSH sozinho não garante que um processo possa capturar ou controlar a área de trabalho. O primeiro marco técnico é verificar lançamento de agente na sessão interativa, captura da janela e entrada direcionada, sem desconectar usuários, alterar política de RDP ou desativar bloqueio de tela. Se isso não for possível com o ambiente atual, apresentar o impedimento em vez de entregar uma interface com controle simulado.

Bloqueio ou desconexão da sessão gráfica podem interromper a ponte. O produto deve mostrar indisponibilidade e parar entrada, sem tentar alterar configurações de segurança para contornar isso.

## Acesso e ciclo de vida

- Servidor inicialmente vinculado a loopback; navegador do Mac acessa por túnel SSH. WebRTC deve ser validado separadamente: sinalização via túnel não garante caminho para mídia. A rede local entre Mac e Windows é candidata; não assumir que portas UDP estão acessíveis.
- Caso não haja caminho de mídia local utilizável sem alterar firewall, usar transporte de quadros pelo canal HTTP/WebSocket autenticado no túnel para esta primeira versão, com limitação de desempenho explicitada.
- Credencial exclusiva da aplicação, gerada localmente e armazenada fora dos fontes; não reutilizar senha SSH. Cookies de sessão protegidos conforme o transporte e validação de origem/CSRF para ações.
- Tokens não vão em URLs. Limitar taxa e tamanho das mensagens, validar eventos e expirar sessão ociosa. A duração pode ser definida pelo implementador e documentada.
- Falha de autenticação impede vídeo e entrada. Desconectar para captura e controle; o agente encerra apenas a conexão que abriu quando puder identificá-la de forma confiável. Não encerrar o serviço global nem outras sessões AnyDesk.
- Logs registram estados e erros, sem senhas, conteúdo da tela ou teclas digitadas.

## Organização e entrega

Código em subdiretório independente `anydesk-web-bridge/`, sem mudanças nos projetos Solar Casa, corte-ai ou investigação Protheus. Instalação Windows em diretório próprio dentro do perfil autorizado, com dependências isoladas. Não modificar binário, licença ou configuração de autenticação do AnyDesk.

Entregar fontes, instruções de iniciar/parar a ponte e o túnel, limites conhecidos, endereço local funcional quando validado e resultados dos testes. Configuração de inicialização permanente fica fora da primeira entrega; processos e artefatos criados precisam ser identificáveis e removíveis.

## Critérios de aceitação

1. Usuário sem autenticação não acessa controle nem captura; origem indevida e mensagens malformadas são rejeitadas.
2. ID válido inicia a conexão correta sem interpretação por shell; ID inválido não executa processo.
3. Uma janela real do AnyDesk chega ao navegador; redimensionamento não desloca cliques.
4. Aceitação/rejeição e indisponibilidade são apresentadas sem sucesso fictício.
5. Mouse e teclado funcionam em um computador remoto de teste autorizado, com modificadores liberados ao perder conexão.
6. Perder foco ou minimizar a janela não dirige entrada a outro aplicativo nem expõe seu conteúdo.
7. Desconectar e parar a ponte preservam outras sessões e projetos.

O teste completo precisa de um segundo equipamento/ID AnyDesk autorizado e alguém para aceitar a conexão. Ainda não há ID de destino fornecido. Até esse teste, declarar apenas os componentes efetivamente verificados, sem afirmar controle remoto de ponta a ponta.

## Escolhas deixadas ao implementador

Bibliotecas de captura e IPC, estrutura dos módulos, porta local disponível, controles visuais e testes unitários/integrados. Preferir a solução mais simples que satisfaça isolamento da janela, autenticação e estados verdadeiros. Não é necessário reproduzir marca ou aparência oficial do AnyDesk.
