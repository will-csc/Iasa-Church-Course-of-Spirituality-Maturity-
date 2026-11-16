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

## Instalação rápida

```bash
git clone https://github.com/will-csc/Iasa-Church-Course-of-Spirituality-Maturity-.git
cd Iasa-Church-Course-of-Spirituality-Maturity-
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy config.ini.example config.ini
```

Edite o `config.ini`:

- `MASTER_USER` / `MASTER_PASSWORD` — login do Apóstolo  
- `AUTHTOKEN` — token do ngrok (se quiser link ngrok)  
- `JITSI_ROOM_NAME` — nome da sala de chamada  

Coloque o PDF do curso em:

`data/784656217-CURSO-DE-MATURIDADE-NO-ESPIRITO-1.pdf`

(ou ajuste o caminho em `app.py` se usar outro arquivo.)

## Como rodar

**Opção 1 — atalho Windows**

```text
run.bat
```

**Opção 2 — terminal**

```bash
.venv\Scripts\python.exe app.py
```

No console e na tela de login aparece o **link externo** para compartilhar com os fiéis.  
**Não desligue o PC** enquanto o encontro estiver ativo.

## Logins padrão (após primeira execução)

O sistema cria contas iniciais (senha = `Nome` + `123`), por exemplo:

| Nome    | Senha       |
|---------|-------------|
| William | William123  |
| Stela   | Stela123    |
| Peter   | Peter123    |
| Saraiva | Saraiva123  |
| Bruna   | Bruna123    |
| Felipe  | Felipe123   |
| Carol   | Carol123    |
| Paulo   | Paulo123    |

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
