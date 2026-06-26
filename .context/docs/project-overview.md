---
type: doc
name: project-overview
description: High-level overview of the project, its purpose, and key components
category: overview
generated: 2026-06-26
status: filled
scaffoldVersion: "2.0.0"
---

# Project Overview

## 1. Project Overview
Este projeto consiste em uma aplicação Python empacotada em Docker, desenvolvida para processar jornadas de usuários a partir do BigQuery (Google Analytics sample). A aplicação aplica modelos avançados de atribuição multi-touch (Markov Chains e Shapley Value) para distribuir o crédito de conversão entre diferentes canais de marketing (Organic Search, Social, Direct, Referral, Paid Search, etc.). O resultado final é exportado em formato Parquet para ser visualizado no Grafana (via DuckDB) e Power BI, fornecendo insights profundos sobre o funil de conversão Omni-Channel.

## 2. Codebase Reference
> **Semantic Snapshot**: Use `context({ action: "getMap", section: "all" })` for generated stack, architecture layers, key files, and dependency hotspots.

## 3. Quick Facts
- Root: `/mnt/sda1/marketing-attribution`
- Languages: Python 3.11, SQL
- Entry: `src/main.py` (a ser criado)
- Semantic snapshot: `context({ action: "getMap", section: "all" })`

## 4. Entry Points
- Server/Job: `src/main.py`
- Docker: `Dockerfile` & `docker-compose.yml`

## 5. Key Exports
- Modelos de Atribuição (Markov Chains e Shapley Value)
- Conexão e ingestão de dados via BigQuery API
- Exportação Parquet com DuckDB

## 6. File Structure & Code Organization
- `docs/` — Documentação do projeto (incluindo o PRD)
- `src/` — Código fonte Python
- `data/` — Volume para artefatos gerados e cache
- `credentials/` — Chaves de acesso (não versionadas)

## 7. Technology Stack Summary
- **Linguagem Principal**: Python 3.11-slim
- **Ambiente**: Docker (Standalone container)
- **Manipulação de Dados**: Pandas, NetworkX
- **Banco de Dados/Armazenamento**: BigQuery (Origem), DuckDB (Transformação Local), Parquet (Destino)
- **Visualização**: Grafana, Power BI

## 8. Core Framework Stack
- **Data Engineering**: Processamento via scripts Python utilizando a API do Google Cloud BigQuery.
- **Data Science**: Implementação matemática de cadeias de Markov usando `NetworkX` e lógica customizada para Shapley Value usando teoria dos jogos cooperativos.

## 9. UI & Interaction Libraries
A aplicação é um job em background, sem interface de usuário nativa. As interações visuais são delegadas para o **Grafana** (dashboards operacionais e de desempenho) e **Power BI** (análise de negócios corporativos).

## 10. Development Tools Overview
- GitHub CLI (`gh`)
- Docker CLI & Docker Compose
- MCP (Model Context Protocol) integrado com Claude/Gemini para contexto de BigQuery e versionamento

## 11. Getting Started Checklist
1. Clonar o repositório.
2. Adicionar as chaves de serviço do GCP em `credentials/gcp-sa-key.json`.
3. Revisar `PROJECT_SETUP.md` para as orientações de setup de ambiente local.
4. Executar `docker-compose up --build` (quando o Milestone 1 estiver completo).

## 12. Next Steps
Atualmente, estamos focados no **Milestone 1 (Foundation)** para configurar o contêiner Docker e os módulos de logging/configuração.
