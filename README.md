# Ponte AnyDesk

Interface local para usar o AnyDesk do Windows TI-LOCAL pelo navegador do Mac. O AnyDesk original faz a conexão remota; este projeto transmite somente sua janela e encaminha entrada com verificação de foco. Não é um cliente independente do protocolo AnyDesk.

**Estado:** interface, autenticação, transmissão real da janela e ativação do controle na ponte validadas; 25 testes passaram no Windows e o teste de navegador confirmou imagem real, login e logout. A última tentativa para o destino informado mostrou “Dispositivo Offline”. Mouse/teclado de ponta a ponta ainda dependem de o destino voltar a ficar online e aceitar a conexão; não foram declarados validados.

O REA 6.5.0 foi usado para inspecionar o AnyDesk instalado. A ponte usa o aplicativo original e APIs de janela do Windows, sem reconstruir seu protocolo. A captura inicial com PrintWindow falhou no conteúdo; a versão atual usa Windows Graphics Capture por HWND exato.


## Acesso

1. No Windows, executar PowerShell como administrador na pasta do projeto: `scripts\start-windows.ps1`. A tarefa usa o usuário interativo `TI-LOCAL\ti-it`, sem guardar sua senha e sem inicialização automática no boot.
2. No Mac, executar `./scripts/tunnel.sh` e manter o terminal aberto.
3. Abrir **http://127.0.0.1:8765** (usar esse endereço exato).
4. A senha da aplicação fica em `.runtime/password.txt`. Ela é exclusiva desta ponte e não é a senha do Windows. O arquivo no Windows tem acesso restrito aos usuários envolvidos e administradores; a cópia local deve manter permissão 600.
5. Informar um ID AnyDesk autorizado e aguardar aceitação no destino. Conferir o estado na imagem: a ponte não interpreta automaticamente a aceitação remota.
6. Se houver várias janelas, selecionar a sessão desejada em **Janela do AnyDesk**. Usar **Ativar controle** e manter o canvas em foco. Se o Windows recusar a ativação, selecionar a janela do AnyDesk na sessão Windows. Isso afeta o foco e o mouse de `ti-it`.

Para encerrar o controle, usar **Desconectar**. Esse botão encerra a transmissão e o controle da ponte. A sessão nativa é preservada: para encerrar a conexão remota, use o próprio AnyDesk. A CLI pode reutilizar processos, portanto a ponte não presume propriedade de janelas novas. Fechar navegador libera teclas e mouse. Para parar o servidor, executar `scripts\stop-windows.ps1` no Windows. Ctrl+C encerra o túnel no Mac.

## Instalação isolada no Windows

Python 3.12 de 64 bits, Windows 11, AnyDesk instalado no caminho padrão e sessão gráfica ativa são necessários.

```powershell
C:\Python312\python.exe -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.\scripts\start-windows.ps1
```

O projeto precisa ser legível pelo usuário interativo e `.runtime` precisa ser gravável somente pelos usuários envolvidos, SYSTEM e administradores. A implantação inicial configura esses direitos na pasta própria; não muda permissões do perfil inteiro. O serviço escuta apenas em `127.0.0.1`, não exige abertura de firewall e recusa Host/Origin diferentes do configurado.

## Limites desta versão

- Uma sessão de controle por vez, transporte JPEG/WebSocket limitado a aproximadamente 10 quadros/s antes do custo de captura/rede. Não é vídeo de alta fluidez.
- Sem áudio, clipboard, arquivos, múltiplos monitores, Ctrl+Alt+Del ou controle do desktop seguro/UAC.
- Bloqueio, desconexão ou suspensão gráfica da sessão RDP podem impedir captura/entrada. Nenhuma política RDP ou proteção de tela é alterada para contornar isso.
- Somente a janela AnyDesk selecionada pode ser capturada. Nenhum fallback captura o desktop inteiro.
- Atalhos reservados do Windows da ponte são bloqueados. Mapeamento de teclado usa teclas físicas e depende do layout do Windows.
- A mídia não é gravada; logs não guardam teclas nem senhas. Evidências de teste locais ficam fora do Git.
- Acesso público pela internet não está configurado. O HTTP local é transportado por SSH; não vincular o serviço a uma interface pública.

## Desenvolvimento e verificação

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
node --check web/app.js
```

O limite do sistema operacional é substituído por um adaptador de teste na suíte HTTP. Isso verifica autenticação, exclusividade, validação e limpeza, **não prova captura ou controle reais**. `scripts/probe_windows.py` testa a captura dentro da sessão Windows; `scripts/check_browser.py` verifica navegador e túnel usando uma cópia local da credencial. Este último exige Playwright e o Google Chrome no Mac. Os testes não iniciam uma conexão AnyDesk remota.

Projeto aprovado: `../docs/superpowers/specs/2026-11-05-anydesk-web-bridge-design.md`.
