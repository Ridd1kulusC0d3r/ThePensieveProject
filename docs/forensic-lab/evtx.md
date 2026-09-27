# Forensic LAB — EVTX

O EVTX é a primeira família de artefatos pesados do Pensieve.

Ele continua **fora do registry padrão**. Para usá-lo é necessário instalar o extra e ativar explicitamente o gate de laboratório.

## Instalação

```bash
python -m pip install '.[evtx]'
```

## Diagnóstico

```bash
pensieve-timeline doctor
```

A saída deve indicar:

```json
"optional_capabilities": {
  "evtx": true
}
```

## Ingestão

```bash
pensieve-timeline ingest Security.evtx \
  --extended-parsers \
  -o timeline.jsonl \
  --sqlite case.db
```

Sem `--extended-parsers`, o Pensieve recusa `.evtx` por design.

## Contrato EVTX v2

Cada registro normalizado preserva:

- `event_id` canônico do Pensieve;
- `provider`;
- `event_code`;
- `channel`;
- `computer`;
- `EventRecordID` em `record_locator`;
- `Execution ProcessID/ThreadID`;
- `Security UserID`;
- `Correlation ActivityID` quando presente;
- `EventData`;
- `UserData`;
- SHA-256 do XML do registro em `raw.xml_sha256`.

Campos duplicados em `EventData` ou `UserData` são preservados como listas em vez de sobrescritos.

## Exemplo normalizado

```json
{
  "artifact_type": "evtx",
  "parser": "python-evtx",
  "parser_version": "2",
  "provider": "Microsoft-Windows-Sysmon",
  "event_code": "1",
  "record_locator": "event_record_id:42",
  "raw": {
    "system": {},
    "event_data": {},
    "user_data": {},
    "xml_sha256": "..."
  }
}
```

## Fail closed

O parser interrompe a ingestão se um registro não puder ser convertido para XML válido, se não possuir `System` ou se não houver `TimeCreated`.

A escolha é deliberada: um parser forense não deve esconder silenciosamente registros que não conseguiu interpretar.

## Scoring provider-aware

Event IDs não são globalmente únicos entre providers.

Por exemplo, `EventID 1` recebe a regra `sysmon-process-create` somente quando o provider/fonte é Sysmon.

```text
EventID=1 + Microsoft-Windows-Sysmon
    -> regra Sysmon

EventID=1 + outro provider
    -> NÃO recebe automaticamente regra Sysmon
```

## Validação unitária

O CI padrão usa XML sintético para verificar:

- System;
- Execution;
- Security;
- EventData;
- UserData;
- campos duplicados;
- hash do XML;
- scoring provider-aware;
- falha em XML inválido;
- falha quando `TimeCreated` está ausente.

Esses testes não precisam baixar um arquivo EVTX.

## Validação com binário real

O workflow:

`.github/workflows/integration-evtx.yml`

é **somente manual**.

No GitHub:

```text
Actions
  -> Forensic LAB — EVTX
  -> Run workflow
```

Ele baixa um fixture fixado por commit de EVTX-ATTACK-SAMPLES, verifica tamanho e SHA-256, instala apenas o extra EVTX, processa o binário pelo gate `--extended-parsers` e valida o contrato canônico.

Como saída do workflow ficam disponíveis por 7 dias:

- `timeline.jsonl`;
- `evtx-case.db`.

## Estado de maturidade

**YELLOW / LAB**

Já demonstrado:

- parsing de binário EVTX real fixado;
- proveniência por EventRecordID;
- provider e Event ID;
- Sysmon;
- EventData/UserData;
- integridade do XML normalizado;
- Linux CI manual.

Ainda falta para promoção adicional:

1. ampliar corpus para Security/System/PowerShell/Sysmon;
2. incluir fixtures com EventData e UserData variados;
3. comparar resultados com implementação independente, preferencialmente Dissect ou Plaso;
4. medir registros processados, tempo e memória;
5. testar arquivos parcialmente corrompidos;
6. validar comportamento em Windows e macOS com corpus real.

Portanto, "o fixture passou" não é sinônimo de "todo EVTX do planeta está validado". Humanos já fizeram estragos suficientes com frases desse tipo.
