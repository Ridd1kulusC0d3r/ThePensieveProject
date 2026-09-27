# AI Reasoning: Evidence Packet v2 + Qwen

A camada de IA do Pensieve é **derivada**. Ela não altera eventos, entidades, hashes ou a timeline.

```text
ForensicEvent + EntityMention
          |
          v
   Evidence Packet v2
          |
          | read-only boundary
          v
    Local Qwen adapter
          |
          v
 strict JSON parser
          |
          v
 citation validator
          |
          v
 calibrated support
          |
          v
 AI Reasoning Report
```

## Evidence Packet v2

Gere o pacote sem executar modelo:

```bash
pensieve-timeline evidence-packet timeline.jsonl   --entities entities.jsonl   -o evidence-packet.json
```

O pacote contém apenas uma visão limitada dos eventos. Por padrão:

- `raw` não é enviado;
- `source_path` não é enviado;
- cada evento recebe `event_digest` SHA-256;
- o pacote recebe `packet_sha256`;
- a seleção é cronológica, não guiada por score de risco;
- cada entidade mantém `mention_id`, normalização, extrator e `evidence_hash`.

Isso permite auditar exatamente o que um modelo recebeu.

## Executar Qwen

```bash
python -m pip install '.[llm]'

pensieve-timeline reason timeline.jsonl entities.jsonl   --model Qwen/Qwen3-0.6B   --packet-output evidence-packet.json   -o intelligence.json
```

`llm-summary` continua como alias de compatibilidade.

## Contrato de saída

O modelo só pode retornar:

- `summary`;
- `claims`;
- `uncertainties`;
- `next_questions`.

Cada claim deve conter:

- `level`: `observation`, `inference` ou `hypothesis`;
- `statement`;
- `evidence_event_ids`;
- `rationale`;
- `alternatives`;
- `reported_confidence` opcional.

Qualquer claim sem `event_id` válido é rejeitado.

Campos como `events`, `corrected_events`, patches ou uma timeline substituta também são rejeitados.

## Hipóteses e alternativas

Uma hipótese precisa trazer pelo menos uma explicação alternativa.

Exemplo conceitual:

```text
Hipótese:
  "Os eventos podem integrar a mesma sequência operacional."

Evidência:
  event-A
  event-B

Alternativa:
  "Os eventos podem representar atividade rotineira independente."
```

A ferramenta não escolhe automaticamente uma hipótese como verdade.

## Confidence calibration

O Pensieve mantém duas coisas diferentes:

1. `reported_confidence`: autoconfiança declarada pelo modelo;
2. `calibrated_support`: score estrutural calculado pelo Pensieve.

A autoconfiança do modelo **não entra** no cálculo do suporte.

A base estrutural considera:

- número de eventos citados;
- diversidade de fontes/artefatos;
- nível epistemológico da claim.

Fatores de nível:

| Claim | Fator |
|---|---:|
| observation | 1.00 |
| inference | 0.80 |
| hypothesis | 0.65 |

O resultado recebe `low`, `moderate` ou `high`.

**Esse score não é probabilidade de verdade.**

Ele mede apenas a quantidade/variedade estrutural de evidência citada segundo uma regra transparente.

## Proteção contra alteração da evidência

Antes da chamada ao modelo, o packet é verificado e fingerprintado.

Depois da geração:

1. o packet original é fingerprintado novamente;
2. qualquer alteração causa falha;
3. a resposta é parseada como um único objeto JSON;
4. blocos de reasoning do provedor não são persistidos;
5. campos inesperados são rejeitados;
6. todos os `event_id` são validados contra o packet;
7. somente então o relatório derivado é salvo.

A IA nunca recebe uma função para gravar na timeline.

## Schemas

Contratos machine-readable:

- `schemas/evidence-packet-v2.schema.json`
- `schemas/ai-reasoning-payload-v2.schema.json`

Eles podem ser usados por outros modelos ou ferramentas sem depender do Qwen.

## Regra epistemológica

```text
model output != evidence
reported confidence != probability
citation != proof
hypothesis != conclusion
```
