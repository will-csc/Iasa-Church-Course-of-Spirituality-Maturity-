# Curso de Maturidade Espiritual — IASA

Aplicação local para encontros online da igreja: login dos fiéis, sala com PDF sincronizado, destaque (pincel) do Apóstolo e chamada embutida (Jitsi), com link externo via ngrok ou Cloudflare Tunnel.

## O que faz

- Login de fiéis (nome + senha) e login do **Apóstolo**
- PDF padrão do curso (todos veem o mesmo material)
- Cada pessoa pode mudar de página; há aviso de **qual página o Apóstolo está**
- Pincel amarelo do Apóstolo para grifar trechos (visível para todos)
- Chamada de áudio/vídeo via Jitsi na mesma tela
- Layout pensado para **celular** (abas Material / Chamada)
- Link público gerado ao iniciar (ngrok, se houver token; senão Cloudflare)

## Requisitos

- Windows (pensado para PC do Apóstolo)
- Python 3.10+
- Conta ngrok (opcional, mas recomendada) — [authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)
- Ngrok instalado no sistema (ex.: `winget install Ngrok.Ngrok`) e atualizado (`ngrok update`)

## Uso rápido (recomendado)

```bash
git clone https://github.com/will-csc/Iasa-Church-Course-of-Spirituality-Maturity-.git
cd Iasa-Church-Course-of-Spirituality-Maturity-
```

Depois dê **duplo clique** em:

- **`Iniciar-Curso.exe`** — não precisa ter Python instalado  
- ou **`Iniciar.bat`** — tenta o `.exe`; se não houver, usa o Python (`run.bat`)

Na primeira execução o app cria o `config.ini`. Edite senha/token se quiser e abra o `.exe` de novo.

No console e na tela de login aparece o **link externo**.  
**Não feche a janela preta** enquanto a reunião estiver ativa.

### Windows pode avisar sobre o `.exe`

É normal em arquivos novos. Em “Mais informações” → **Executar assim mesmo**.

### Ngrok (opcional)

Para link `*.ngrok-free.app`, instale o ngrok no PC (`winget install Ngrok.Ngrok`, depois `ngrok update`) e coloque o `AUTHTOKEN` no `config.ini`.  
Sem ngrok, o app tenta Cloudflare Tunnel automaticamente.

## Gerar o `.exe` de novo (desenvolvedor)

Se alterar o código Python:

```text
run.bat          (cria .venv e deps)
build_exe.bat    (gera Iniciar-Curso.exe)
```

## Alternativa com Python (sem .exe)

1. Instale Python 3.10+ com **Add to PATH**
2. Duplo clique em `run.bat`

Edite o `config.ini`:

- `MASTER_USER` / `MASTER_PASSWORD` — login do Apóstolo  
- `AUTHTOKEN` — token do ngrok (opcional)  
- `ROOM_NAME` em `[jitsi]` — nome da sala de chamada

## Logins padrão (após primeira execução)

O sistema cria contas iniciais (senha = `Nome` + `123`), por exemplo:

Nomes e senhas **não diferenciam maiúsculas/minúsculas**.

O Apóstolo também pode criar/remover contas pelo painel da sala.

## Uso na sala

**Todos**

- Navegar no PDF (Anterior / Próxima / número da página)
- Ver o aviso “Apóstolo na pág. X” e usar **Ir para lá**
- Participar da chamada (aba **Chamada** no celular)

**Apóstolo**

- Controlar a página de referência do grupo
- Ativar **Pincel** e grifar o PDF; **Limpar grifo** na página atual
- Bloquear/desbloquear novos logins
- Enviar outro PDF ou voltar ao PDF padrão
- Criar logins de fiéis
- Copiar o link externo

## Estrutura principal

```text
app.py              → servidor Flask + Socket.IO
room_state.py       → página, PDF, lock, destaques
users.py            → contas dos fiéis
tunnel.py           → ngrok / Cloudflare
templates/          → login e sala
static/             → CSS, JS, logo
data/               → PDF do curso (+ users.json local, não versionado)
config.ini.example  → modelo de configuração
```

## Observações

- O arquivo `config.ini` **não** vai para o Git (contém senhas/token). Use sempre o `.example`.
- `data/users.json` também é local e não versionado.
- No plano gratuito do ngrok, a URL muda a cada reinício e pode aparecer uma página de aviso na primeira visita.
- A chamada usa servidores do Jitsi (`meet.jit.si`); o PC só serve a página, o PDF e a sincronização.

## Licença

Uso interno da igreja / curso IASA. Ajuste conforme a necessidade da congregação.
