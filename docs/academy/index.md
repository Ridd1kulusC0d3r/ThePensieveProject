# Pensieve DFIR + OSINT Academy

A Academy ensina uma **primeira investigação reproduzível** antes de apresentar formatos forenses pesados. O objetivo não é decorar comandos; é aprender a distinguir evidência, correlação, inferência e hipótese.

## Escolha uma trilha

| Trilha | Para quem | Dataset | Saída principal |
|---|---|---|---|
| [DFIR](track-dfir.md) | primeira timeline e raciocínio forense | `dfir.csv` | timeline + correlações + hipótese |
| [OSINT](track-osint.md) | extração e vínculo de entidades | `osint.csv` | entidades + grafo de coocorrência |
| [DFIR + OSINT](track-hybrid.md) | investigação integrada | `hybrid.csv` | evidence graph + Evidence Packet v2 |

Todas começam pelo mesmo núcleo:

**C00 Orientar → C01 Preservar → C02 Normalizar**

Depois o aluno segue apenas a trilha escolhida. Nada obriga alguém estudando DFIR a baixar modelo de NER, porque sofrimento computacional não é objetivo pedagógico.

## Método

Cada missão usa o mesmo ciclo:

1. **Microconceito** — o que você precisa saber antes do comando.
2. **Ação** — um comando ou pequena tarefa.
3. **Saída observável** — o que deve aparecer.
4. **Pergunta investigativa** — o que você consegue concluir.
5. **Limite** — o que a saída não prova.
6. **Checkpoint** — evidência de que você entendeu antes de avançar.

O catálogo completo e machine-readable está em `academy/catalog.json`.

## First Investigation

O caminho recomendado é o notebook:

`colab/first_investigation.ipynb`

Ele possui um seletor:

```python
TRACK = "DFIR"   # ou "OSINT" / "HYBRID"
```

O notebook usa apenas datasets sintéticos pequenos por padrão. GLiNER e Qwen permanecem desativados até o aluno habilitá-los conscientemente.

## Contrato epistemológico

```text
evento != interpretação
score != veredito
correlação != causalidade
entidade normalizada != identidade verificada
saída de IA != evidência
hipótese != conclusão
```

## Para tutores de IA

`academy/ai-manifest.json` define como um tutor deve ensinar as missões. Ele deve pedir que o aluno interprete a evidência e apontar os campos relevantes quando houver erro, em vez de simplesmente despejar a resposta.

O progresso pode ser representado pelo schema `schemas/academy-progress.schema.json`.
