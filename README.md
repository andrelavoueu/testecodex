# Plataforma Operacional de Viagens Corporativas

Este repositório inicia a construção de uma aplicação interna para agência de viagens corporativas.

## Arquitetura proposta (em etapas)

### Etapa 1 — Ingestão e estruturação dos e-mails (MVP atual)
Objetivo: transformar e-mails operacionais em registros estruturados de viagem.

- Conector de e-mail (inicialmente via arquivos `.txt`, depois Gmail API)
- Parser de conteúdo operacional
- Normalização de campos
- Persistência em banco SQLite
- Indicador calculado: antecedência de compra (dias)

### Etapa 2 — Sincronização de caixas da equipe + API/Dashboard (entregue)
Objetivo: trazer os dados para um painel interno em navegador.

- Sincronizador IMAP para múltiplas contas (compatível com Gmail)
- Persistência idempotente no SQLite
- API HTTP para consultas de viagens e KPIs
- Dashboard web simples para visualização operacional

### Etapa 3 — Comunicação automática com viajantes
Objetivo: envio programado de mensagens personalizadas.

- Motor de templates de mensagens
- Gatilhos por data da viagem (D-7, D-2, D-1 etc.)
- Tipos de comunicação:
  - dicas de destino
  - lembrete de check-in
  - alertas pré-embarque

### Etapa 4 — Integrações e governança
Objetivo: produção com segurança e escalabilidade.

- OAuth para múltiplas contas Gmail da operação
- Logs, rastreabilidade e monitoramento
- Controle de permissões por perfil
- Tratamento de falhas e reprocessamento

## Módulos funcionais disponíveis

### 1) Ingestão por arquivos locais (`.txt`)

Lê e-mails operacionais em texto (`sample_emails/*.txt`), extrai campos, calcula antecedência e salva em `data/travel_ops.db`.

```bash
python -m src.travel_ops.ingest --input-dir sample_emails --db-path data/travel_ops.db --list
```

### 2) Sincronização de múltiplas contas por IMAP

Use `config.imap.example.json` como base e configure variáveis de ambiente com as senhas/app-passwords.

```bash
cp config.imap.example.json config.imap.json
# export EMAIL_PASS_OPERACAO1='***'
# export EMAIL_PASS_OPERACAO2='***'
python -m src.travel_ops.sync_inboxes --config config.imap.json --db-path data/travel_ops.db
```

### 3) API + dashboard interno no navegador

Suba o servidor HTTP:

```bash
python -m src.travel_ops.server --db-path data/travel_ops.db --host 0.0.0.0 --port 8000
```

Acesse:
- `http://localhost:8000/` (dashboard)
- `http://localhost:8000/api/trips` (lista de viagens)
- `http://localhost:8000/api/kpis` (indicadores)
- `http://localhost:8000/health` (saúde)

## Formato esperado de conteúdo operacional

```txt
Cliente: Empresa X
Viajante: Nome Sobrenome
Data da viagem: 2026-04-10
Destino: Lisboa
Consultor: Ana Souza
Status: Emitido
Data da compra: 2026-03-25
```

## Próximo passo recomendado

Implementar OAuth Gmail (substituindo senha IMAP), agendamento da sincronização e módulo de comunicação automática para o viajante com templates por destino e gatilhos por data.
