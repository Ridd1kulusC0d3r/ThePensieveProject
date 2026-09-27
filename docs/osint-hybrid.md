# OSINT híbrido: extração sem confundir evidência com identidade

A camada OSINT trabalha **sobre dados já presentes no caso**. Ela não consulta serviços externos automaticamente.

```text
ForensicEvent
   +--> regex determinístico ----+
   +--> GLiNER opcional ---------+--> EntityMention
                                      |
                                      +--> normalização conservadora
                                      +--> deduplicação multi-extrator
                                      +--> Entity Graph
```

## Contrato de uma entidade

Cada `EntityMention` preserva:

- `event_id`: evento que contém a evidência;
- `text`: trecho original, sem substituição pelo modelo;
- `start/end`: offsets exatos;
- `label`: rótulo canônico;
- `normalized_value`: valor para comparação e agregação;
- `score`: confiança produzida pelo extrator;
- `confidence_kind`: `deterministic`, `model` ou `derived`;
- `extractor`: extrator principal;
- `corroborated_by`: extratores que encontraram a mesma menção;
- `evidence_hash`: SHA-256 do vínculo entre evento, campo, offsets e texto.

O valor normalizado **não substitui** o valor observado.

## Normalização conservadora

A normalização existe para comparação, não para afirmar identidade.

Exemplos:

```text
Ops@Example.ORG -> ops@example.org
CVE-2026-12345  -> cve-2026-12345
2001:0db8::1    -> 2001:db8::1
```

Telefones têm pontuação removida, mas o sistema **não inventa código de país**. URLs normalizam esquema/host e portas padrão, preservando caminho e query.

## Deduplicação

Se regex e GLiNER encontrarem exatamente o mesmo span com o mesmo valor canônico:

```text
regex:email --------+
                    +--> uma EntityMention
GLiNER -------------+       corroborated_by=[...]
```

O extrator determinístico é preferido como fonte principal quando existe, mas a corroboracão do modelo é mantida.

Ocorrências diferentes do mesmo valor no mesmo documento continuam sendo menções distintas.

## GLiNER

```bash
pip install '.[osint]'
pensieve-timeline entities timeline.jsonl --gliner -o entities.jsonl
```

O modelo padrão é `urchade/gliner_multi-v2.1`. Os rótulos podem ser alterados com `--labels`.

Para reduzir alucinação estrutural, a saída do modelo não é aceita como texto livre. O Pensieve exige offsets válidos e recorta o texto diretamente da evidência original. Predições com spans inválidos são descartadas.

## Grafo

Nós de entidade são agregados por:

```text
(label canônico, normalized_value)
```

Uma aresta `co_occurrence` significa apenas que as entidades apareceram no mesmo evento.

**Não significa:**

- mesma pessoa;
- mesma conta;
- propriedade;
- autoria;
- vínculo social;
- causalidade.

Essas relações exigem evidência adicional.

## Persistência

O SQLite mantém entidades em uma camada derivada, separada da tabela de eventos. Bancos existentes recebem as novas colunas por migração aditiva:

- `normalized_value`
- `confidence_kind`
- `evidence_hash`
- `corroborated_by_json`

A timeline original não é alterada.

## Três fronteiras

1. **Extração**: este trecho aparece na evidência.
2. **Correlação**: estes trechos/eventos compartilham contexto segundo regras explícitas.
3. **Inferência**: uma hipótese explica os dados.

Nenhuma delas, sozinha, comprova identidade, causalidade ou intenção.

## Próxima camada

Qwen permanece separado desta etapa. Ele recebe um Evidence Packet derivado e nunca deve modificar `ForensicEvent` ou `EntityMention`.

## Privacidade

- nenhum enriquecimento web automático;
- nunca modifique a evidência original;
- registre origem e data de coleta de fontes públicas;
- trate dados pessoais como material investigativo, não como autorização para exposição;
- mantenha fonte pública, evidência do caso e inferência em camadas distintas.
