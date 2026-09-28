# Frontend simples no Google Colab

O Pensieve pode subir uma interface web diretamente no runtime do Colab, na porta **3000**.

Notebook:

`colab/pensieve_frontend.ipynb`

## O que a interface oferece

- upload de CSV / TSV / JSONL;
- escolha entre **Forensic Core** e **AI Analyst**;
- GLiNER e Qwen ligados por padrão no perfil AI;
- cards de eventos, correlações, entidades e claims;
- timeline tabular;
- entidades normalizadas;
- AI Reasoning com citações por `event_id`;
- lista de artefatos gerados;
- abertura do relatório HTML completo.

## Subir manualmente

Instale:

```bash
python -m pip install -e '.[ui,osint,llm]'
```

Inicie:

```bash
pensieve-web \
  --host 0.0.0.0 \
  --port 3000 \
  --case-root /content/pensieve-cases \
  --upload-root /content/pensieve-uploads
```

No Colab:

```python
from google.colab import output
output.serve_kernel_port_as_window(3000)
```

O Colab cria uma URL semelhante a:

```text
https://3000-...prod.colab.dev/
```

Essa URL é o proxy da porta 3000 do runtime.

## Perfil Forensic

Selecione:

`Forensic Core · sem IA`

O pipeline gera:

```text
timeline.jsonl
timeline.csv
timesketch.jsonl
correlations.jsonl
case.db
report.html
manifest.json
```

GLiNER e Qwen não são executados.

## Perfil AI

Selecione:

`AI Analyst · GLiNER + Qwen`

Por padrão:

```text
GLiNER = ON
Qwen   = ON
```

O pipeline adiciona:

```text
entities.jsonl
evidence-graph.json
evidence-packet.json
intelligence.json
```

A interface não permite ao Qwen reescrever a timeline. O modelo continua limitado pelo Evidence Packet v2 e pelo validador de citações.

## Timeline já processada

Se o arquivo enviado for um `timeline.jsonl` produzido pela VM Forensic, marque:

`timeline.jsonl já canônica`

Assim o perfil AI reutiliza os eventos existentes sem reaplicar a ingestão/scoring.

## Runtime efêmero

Arquivos ficam em:

```text
/content/pensieve-cases/
/content/pensieve-uploads/
```

até o runtime do Colab ser encerrado. Exporte os casos que quiser preservar.

## Design

A UI é deliberadamente pequena:

```text
FastAPI
  +
HTML/CSS/JS inline
  +
Pensieve ops
```

Não há React, Node, build ou banco adicional. No contexto de Colab, menos dependências significa mais tempo investigando e menos tempo negociando com webpack.
