# OSINT híbrido: GLiNER + Qwen sem misturar evidência e inferência

A camada OSINT trabalha **sobre dados já presentes no caso**. Ela não consulta serviços externos automaticamente.

```text
ForensicEvent
   +--> regex determinístico ----+
   +--> GLiNER opcional ---------+--> EntityMention --> Entity Graph
                                      |
                                      +--> Evidence Packet --> Qwen local
```

Cada `EntityMention` guarda `event_id`, offsets, rótulo, score e extrator. Assim ele pode ser reprocessado sem alterar a timeline.

## Três fronteiras

1. **Extração**: este trecho aparece na evidência.
2. **Correlação**: estes trechos/eventos compartilham contexto.
3. **Inferência**: uma hipótese explica os dados.

Nenhuma delas, sozinha, comprova identidade, causalidade ou intenção.

## GLiNER

```bash
pip install '.[osint]'
pensieve-timeline entities timeline.jsonl --gliner -o entities.jsonl
```

O modelo padrão é `urchade/gliner_multi-v2.1`. Os rótulos podem ser alterados com `--labels`.

## Qwen local

```bash
pip install '.[llm]'
pensieve-timeline llm-summary timeline.jsonl entities.jsonl --model Qwen/Qwen3-0.6B -o intelligence.json
```

O Qwen não recebe `raw` por padrão. O Evidence Packet contém IDs de eventos, mensagens limitadas e entidades observadas. O prompt exige incertezas e IDs de evidência.

## Privacidade

- nenhum enriquecimento web automático;
- nunca modifique a evidência original;
- registre origem e data de coleta de fontes públicas;
- trate dados pessoais como material investigativo, não como autorização para exposição;
- mantenha fonte pública, evidência do caso e inferência em camadas distintas.
