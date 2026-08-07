# AI Lead Factory

Servizio AI per trasformare un input commerciale in un pacchetto pronto: contatti target, messaggi, email e follow-up.

## Cosa fa

1. Trasforma il business inserito in una proposta pronta
2. Genera contatti target da cercare
3. Scrive email, LinkedIn, WhatsApp e follow-up
4. Prepara una base commerciale da vendere subito

## Avvio rapido su Windows CMD

```cmd
cd impresa-ai
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Apri:

```text
http://127.0.0.1:8000
```

## Test

```cmd
.venv\Scripts\python.exe -m pytest
```

## Deploy online

La strada più semplice è Render:

1. Metti il progetto su GitHub.
2. Crea un nuovo Web Service su Render collegando il repo.
3. Usa il `render.yaml` incluso nel progetto.
4. Dopo il deploy apri la tua URL `onrender.com`.

Nota: la versione attuale è perfetta per lavorare online come app live. Se vuoi salvare storico, lead e conversazioni in modo permanente, il passo successivo è collegare un database esterno invece del solo SQLite.

## Struttura

```text
backend/
  api/
  core/
  db/
  models/
  schemas/
  services/
frontend/
  assets/
    css/
    js/
  index.html
tests/
```

Il prodotto funziona anche senza chiave AI, usando risposte locali dimostrative.
