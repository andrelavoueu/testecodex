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

### Etapa 2 — Dashboard interno web
Objetivo: disponibilizar visão operacional para equipe.

- API de leitura dos registros
- Interface web com filtros por cliente, consultor, status e período
- KPIs principais:
  - volume de viagens por período
  - média de antecedência de compra
  - distribuição por status
  - top destinos e clientes

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

## Primeiro módulo funcional implementado

Foi implementado o módulo **Ingestão + Extração + Persistência**.

### O que ele faz

1. Lê e-mails operacionais em texto (`sample_emails/*.txt`)
2. Extrai os campos:
   - cliente
   - viajante
   - data da viagem
   - destino
   - consultor responsável
   - status da viagem
   - data da compra
3. Calcula automaticamente a **antecedência de compra**
4. Salva os registros em banco SQLite (`data/travel_ops.db`)

### Formato esperado do e-mail

```txt
Cliente: Empresa X
Viajante: Nome Sobrenome
Data da viagem: 2026-04-10
Destino: Lisboa
Consultor: Ana Souza
Status: Emitido
Data da compra: 2026-03-25
```

### Executando

```bash
python -m src.travel_ops.ingest --input-dir sample_emails --db-path data/travel_ops.db
```

### Consultando registros rapidamente

```bash
python -m src.travel_ops.ingest --input-dir sample_emails --db-path data/travel_ops.db --list
```

## Próximo passo recomendado

Implementar o conector Gmail API para múltiplas caixas de entrada e agendar a execução da ingestão (cron/job), mantendo o parser e o banco já criados neste MVP.
