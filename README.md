# Plataforma Operacional de Viagens Corporativas

Aplicação interna para sua agência transformar e-mails operacionais em dados estruturados, visualizar indicadores e disparar comunicações automáticas para viajantes.

## Para quem é leigo: por onde começar

### Passo 1) Testar com e-mails de exemplo (sem integrar Gmail ainda)
```bash
python -m src.travel_ops.ingest --input-dir sample_emails --db-path data/travel_ops.db --list
```

### Passo 2) Subir dashboard no navegador
```bash
python -m src.travel_ops.server --db-path data/travel_ops.db --host 0.0.0.0 --port 8000
```
Abra `http://localhost:8000/`.

### Passo 3) Simular mensagens automáticas para viajantes
```bash
python -m src.travel_ops.messaging --db-path data/travel_ops.db --reference-date 2026-05-10 --dry-run
```

---

## Arquitetura em etapas

### Etapa 1 — Ingestão e estruturação dos e-mails (entregue)
- Parser de conteúdo operacional
- Normalização de campos
- Persistência em SQLite
- Cálculo de antecedência de compra

### Etapa 2 — Sincronização de caixas + API/Dashboard (entregue)
- Sync IMAP de múltiplas contas (compatível com Gmail)
- API HTTP (`/api/trips`, `/api/kpis`, `/api/status-breakdown`)
- Dashboard com filtros e paginação

### Etapa 3 — Comunicação automática com viajantes (entregue em MVP)
- Gatilhos por data (D-7, D-2, D-1)
- Dry-run para validação
- Envio SMTP real quando variáveis estiverem configuradas

### Etapa 4 — Governança (próxima)
- OAuth Gmail no lugar de senha IMAP
- Logs centralizados e monitoramento
- Controle de acesso por perfil

---

## Campos extraídos do e-mail operacional

Formato aceito:

```txt
Cliente: Empresa X
Viajante: Nome Sobrenome
Email do viajante: nome@empresa.com
Data da viagem: 2026-04-10
Destino: Lisboa
Consultor: Ana Souza
Status: Emitido
Data da compra: 2026-03-25
```

Campos obrigatórios: cliente, viajante, data da viagem, data da compra, destino, consultor, status.  
Campo opcional: email do viajante.

---

## Sincronização de múltiplas contas (IMAP)

1) Copie o arquivo exemplo:
```bash
cp config.imap.example.json config.imap.json
```

2) Defina as senhas/app-passwords das contas:
```bash
export EMAIL_PASS_OPERACAO1='***'
export EMAIL_PASS_OPERACAO2='***'
```

3) Execute sync:
```bash
python -m src.travel_ops.sync_inboxes --config config.imap.json --db-path data/travel_ops.db
```

---


## Operação contínua (modo produção simplificado)

Se você quer deixar tudo rodando automaticamente (sync + mensagens), use o worker:

```bash
python -m src.travel_ops.worker \
  --config config.imap.json \
  --db-path data/travel_ops.db \
  --interval-seconds 900 \
  --messaging-dry-run
```

- `--once`: executa um ciclo único e encerra (ótimo para teste).
- `--sync-dry-run`: valida sync sem gravar no banco.
- `--messaging-dry-run`: simula envios sem SMTP real.

Exemplo de ciclo único:

```bash
python -m src.travel_ops.worker \
  --config config.imap.json \
  --db-path data/travel_ops.db \
  --once \
  --sync-dry-run \
  --messaging-dry-run \
  --reference-date 2026-05-10
```

---

## API e dashboard

Subir servidor:
```bash
python -m src.travel_ops.server --db-path data/travel_ops.db --host 0.0.0.0 --port 8000
```

Endpoints:
- `GET /health`
- `GET /api/kpis`
- `GET /api/status-breakdown`
- `GET /api/trips?page=1&page_size=10&client=...&consultant=...&status=...`

### Proteção simples por API key (opcional)
Se definir a variável `TRAVEL_OPS_API_KEY`, os endpoints `/api/*` exigirão header `X-API-Key`.

Exemplo:
```bash
export TRAVEL_OPS_API_KEY='minha-chave-interna'
curl -H 'X-API-Key: minha-chave-interna' 'http://127.0.0.1:8000/api/kpis'
```

---

## Mensagens automáticas ao viajante

### 1) Simulação (recomendado primeiro)
```bash
python -m src.travel_ops.messaging --db-path data/travel_ops.db --reference-date 2026-05-10 --dry-run
```

### 2) Envio real por SMTP
Configure:
```bash
export SMTP_HOST='smtp.seu-provedor.com'
export SMTP_PORT='587'
export SMTP_USER='usuario'
export SMTP_PASS='senha'
export SMTP_FROM='operacao@suaagencia.com'
```

Depois execute sem `--dry-run`:
```bash
python -m src.travel_ops.messaging --db-path data/travel_ops.db --reference-date 2026-05-10
```

Tipos automáticos:
- D-7: dicas do destino
- D-2: lembrete de check-in
- D-1: alerta pré-embarque
