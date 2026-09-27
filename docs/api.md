# API REST opcional

A API do Pensieve é uma superfície **somente leitura** sobre o banco SQLite de um caso.

Ela existe para integração com notebooks, dashboards, Timesketch bridges e ferramentas internas sem transformar o serviço web em uma nova fonte de alterações na evidência.

## Instalação

```bash
python -m pip install ".[api]"
```

## Execução

```bash
export PENSIEVE_CASE_DB=/caminho/para/case.db
python -m uvicorn pensieve_timeline.api:create_app --factory --host 127.0.0.1 --port 8000
```

O bind recomendado é `127.0.0.1`. Expor um caso forense na rede sem autenticação seria uma forma especialmente criativa de produzir um segundo incidente.

## Endpoints

| Endpoint | Uso |
| --- | --- |
| `GET /health` | estado do serviço e nome do banco |
| `GET /stats` | contagem das camadas disponíveis |
| `GET /events` | eventos canônicos com filtros |
| `GET /events/{event_id}` | um evento por ID |
| `GET /entities` | menções de entidades derivadas |
| `GET /correlations` | correlações explicáveis |

Por padrão `raw_json` não é retornado em eventos. Use `include_raw=true` somente quando o conteúdo bruto realmente for necessário.

## Segurança e cadeia de custódia

- SQLite é aberto com `mode=ro` e `PRAGMA query_only=ON`.
- Não existem endpoints `POST`, `PUT`, `PATCH` ou `DELETE`.
- CORS permissivo não é habilitado.
- Não há enriquecimento externo automático.
- A API serve dados do caso; ela não transforma inferências em evidência.
