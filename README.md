# Doc Decode

**Understand before you sign.**

Doc Decode reads a rental agreement, loan agreement, hospital bill or government
notice and turns it into something you can act on: the amounts and dates it
actually contains, the sentences worth a second look, and an explanation of each
one in plain English or Malayalam. Everything runs on your own machine.

It is not an AI PDF summariser. The pipeline is deliberately split in two:

- **Python rules** decide *what* matters. Amounts, dates, interest rates, notice
  periods and clause categories come from regular expressions and keyword rules,
  so the same document always gives the same result and nothing is invented.
- **A local LLM** (via Ollama) only rewrites those clauses in simpler words. It
  never decides what is important, and it is never asked to produce a number.

If Ollama is not running, the whole app still works. You get the facts, the
flagged clauses and the deadlines, and the UI says plainly that the plain-language
rewrite is missing rather than faking one.

---

## The problem

A rental agreement, a loan sanction letter, a hospital bill or a government
notice is written to be enforceable, not understood. The person signing it is
usually reading it for the first time, on a phone, in a second language, with no
one to ask. Professional help exists, but it costs more than the dispute and is
concentrated in cities and in English.

Three things go wrong as a result. People sign terms they would have questioned
(an automatic renewal, a 10% late fee, a lock-in with no exit), they miss the one
date that carries a penalty, and they cannot check the arithmetic on a bill that
may simply be wrong.

---

## Impact

Doc Decode targets the moment before the signature, on the device already in the
person's hand:

- **Comprehension** — every amount, date and clause is shown beside the original
  sentence and its page, so the reading can be checked rather than trusted.
- **Language** — the same document works in English and in Malayalam, including
  Malayalam scans read by OCR and spoken aloud by a local speech engine.
- **Action** — deadlines the document actually states become a calendar file,
  and only after the person has ticked them off.
- **Access** — the whole pipeline runs offline on a laptop. No account, no
  upload, no per-page fee and no document leaving the machine, which is what
  makes it practical for legal-aid clinics, panchayat offices and college
  legal-literacy programmes that cannot send client papers to a cloud API.
- **Trust** — Python rules decide what matters and the model only rewrites it,
  so one document always produces the same findings and nothing is invented.

The prototype is measured end to end on its own demo documents (see
[Measured on a real machine](#measured-on-a-real-machine)): a two-page loan
agreement is read, classified, verified and analysed in about two seconds with
the AI step switched off.

---

## Contents

- [The problem](#the-problem)
- [Impact](#impact)
- [What it does](#what-it-does)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running it](#running-it)
- [Demo documents](#demo-documents)
- [Testing](#testing)
- [Audio, and why Malayalam needs an extra step](#audio-and-why-malayalam-needs-an-extra-step)
- [What it can and cannot read](#what-it-can-and-cannot-read)
- [Choosing a model for your GPU](#choosing-a-model-for-your-gpu)
- [Measured on a real machine](#measured-on-a-real-machine)
- [API reference](#api-reference)
- [Privacy and security](#privacy-and-security)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)

---

## What it does

1. **Upload** a PDF, JPG or PNG (drag and drop or file picker).
2. **Extract text** with PyMuPDF. Pages that come back empty — scans — are
   rendered and sent to Tesseract OCR, and only those pages.
3. **Classify** the document by keyword score. If the score is not decisive it
   says "document type uncertain" instead of guessing.
4. **Extract facts** with rules: rent, deposit, loan amount, interest rate, EMI,
   totals, due dates, notice periods and so on. Each fact carries the sentence it
   came from and its page number.
5. **Detect clauses** across 12 categories (auto-renewal, penalties, late fees,
   extra charges, lock-in, early termination, deductions, notice periods,
   interest conditions, obligations, deadlines, one-sided conditions).
6. **Explain** the highest-priority clauses by sending them to Ollama in **one
   batched request**, and validate the reply with Pydantic.
7. **Show** everything beside the original wording, with page numbers, a
   confidence indicator and whether each explanation came from the model or from
   the rule engine.
8. **Answer questions** about the document using TF-IDF retrieval over the
   extracted sentences plus one Ollama call, returning the evidence sentences.
9. **Export deadlines** you have personally ticked as an `.ics` calendar file.
10. **Read it aloud** with the browser's own speech voices.

---

## Architecture

```
React (Vite)  ──POST /api/analyze──▶  FastAPI
                                        │
                                        ▼
                              upload validation
                       (extension + MIME + magic bytes + size)
                                        │
                                        ▼
                        PyMuPDF text  ──▶ empty page? ──▶ Tesseract OCR
                                        │
                                        ▼
                        clean text, split into clause-sized segments
                                   (page numbers kept)
                                        │
            ┌───────────────┬───────────┴───────────┬──────────────────┐
            ▼               ▼                       ▼                  ▼
      classifier      fact extractor         clause detector    deadline extractor
      (keywords)      (regex rules)          (phrase rules)     (cue + date rules)
            └───────────────┴───────────┬───────────┴──────────────────┘
                                        ▼
                      Ollama: ONE batched explanation request
                             (clauses only, never the whole document)
                                        ▼
                        structured JSON → React dashboard
```

The rule layer is the product. The model is a presentation step on top of it.

### Backend modules

| File | Responsibility |
| --- | --- |
| `main.py` | FastAPI routes and error handlers |
| `config.py` | all settings, read from `.env` |
| `schemas.py` | Pydantic models for requests, responses, validated LLM output |
| `pipeline.py` | upload validation and the end-to-end analysis flow |
| `pdf_reader.py` | PyMuPDF extraction with per-page OCR fallback |
| `ocr_reader.py` | Tesseract detection, language resolution, image prep |
| `utils.py` | text cleanup, sentence/clause segmentation |
| `dates.py` | date and money parsing (Indian formats, lakh/crore) |
| `document_classifier.py` | keyword-score classification |
| `fact_extractor.py` | per-document-type fact rules |
| `clause_detector.py` | the 12-category clause rule engine |
| `deadline_extractor.py` | deadline cues plus date resolution |
| `ollama_service.py` | Ollama HTTP client, status checks, JSON parsing |
| `prompts.py` | prompt templates and the untrusted-input fencing |
| `ai_explainer.py` | batched clause explanation and summary |
| `question_answering.py` | TF-IDF retrieval and grounded answers |
| `calendar_export.py` | RFC 5545 `.ics` generation |

### Frontend structure

```
frontend/src/
  components/  Navbar HealthBadge UploadArea ProcessingStatus
               DocumentOverview KeyFacts RiskSummary RiskCard
               LanguageSelector AudioControls AskDocument
               DeadlineList ExtractedTextViewer PrivacyPanel
  pages/       Home.jsx  Analysis.jsx
  services/    api.js
  i18n.js      English and Malayalam interface strings
  App.jsx      state, language switching, health polling
```

---

## Technology stack

**Frontend:** React 18, Vite 6, Tailwind CSS 4, Lucide icons. No router, no state
library, no component library. Production bundle is about 208 KB (64 KB gzipped).

**Backend:** Python, FastAPI, Uvicorn, PyMuPDF, pytesseract, Pillow, Pydantic,
httpx.

**Local AI:** Ollama over its local HTTP API. No cloud AI service, no API key.

**Storage:** none. Uploads live in memory for one request. There is no database.

---

## Prerequisites

| Tool | Needed for | Required? |
| --- | --- | --- |
| Python 3.10+ | the backend | yes |
| Node.js 18+ | the frontend | yes |
| Ollama + a small model | plain-language explanations and Q&A | strongly recommended |
| Tesseract OCR | scanned PDFs and photos | only for scans |
| Tesseract Malayalam data | OCR of Malayalam documents | optional |

Check what you have:

```bash
python --version
node --version
npm --version
```

---

## Installation

### 1. Get the code and create a Python environment

```bash
cd leadathon

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install the Python packages

```bash
pip install -r backend/requirements.txt
```

### 3. Install the frontend packages

```bash
cd frontend
npm install
cd ..
```

If npm warns that `esbuild` has an install script that was not run:

```bash
cd frontend
npm install-scripts approve esbuild
cd ..
```

### 4. Install Ollama and pull a model

Download Ollama from <https://ollama.com/download> and install it, then:

```bash
ollama pull qwen2.5:3b
```

Check it is running:

```bash
ollama list
curl http://localhost:11434/api/tags
```

Any small instruct model works. `llama3.2:3b` and `qwen2.5:7b` are both fine —
put whichever you pulled in `OLLAMA_MODEL`. Nothing is downloaded automatically
by this app, and nothing is fine-tuned.

### 5. Install Tesseract OCR (only if you want to read scans or photos)

**Windows:** install the build from
<https://github.com/UB-Mannheim/tesseract/wiki>, then put the path in `.env`:

```
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

**macOS:**

```bash
brew install tesseract
brew install tesseract-lang   # includes Malayalam
```

**Ubuntu / Debian:**

```bash
sudo apt update
sudo apt install tesseract-ocr
sudo apt install tesseract-ocr-mal   # Malayalam, optional
```

**Malayalam OCR without administrator rights.** `C:\Program Files\...` is not
writable by a normal user, so Doc Decode also looks for a `tessdata` folder in
the project root and points Tesseract at it through `TESSDATA_PREFIX`. That
folder replaces Tesseract's own, so it must hold *every* language you use:

```bash
mkdir tessdata
# copy the packs that shipped with Tesseract
cp "/c/Program Files/Tesseract-OCR/tessdata/eng.traineddata" tessdata/
cp "/c/Program Files/Tesseract-OCR/tessdata/osd.traineddata" tessdata/
# add Malayalam (5.7 MB)
curl -L -o tessdata/mal.traineddata \
  https://github.com/tesseract-ocr/tessdata/raw/main/mal.traineddata
```

Then set `OCR_LANGS=eng+mal` in `.env`. The folder is about 20 MB and is
gitignored. To install system-wide instead, run the Tesseract installer as
administrator and tick **Malayalam** under "Additional language data", then
delete the project `tessdata` folder.

Doc Decode checks which packs are actually present and drops any that are
missing, so a wrong `OCR_LANGS` degrades rather than crashing. The status pill
in the app reports which languages are live.


### 6. Create your `.env`

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

---

## Configuration

Everything lives in `.env` at the project root. Nothing is hardcoded.

| Variable | Default | Meaning |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | where Ollama listens |
| `OLLAMA_MODEL` | `qwen2.5:3b` | model for English |
| `OLLAMA_MODEL_ML` | `gemma2:9b` | model used only for Malayalam (empty = same) |
| `OLLAMA_TIMEOUT` | `240` | seconds to wait for the model |
| `OLLAMA_TIMEOUT_ML` | `420` | longer budget for the Malayalam model |
| `OLLAMA_KEEP_ALIVE` | `30m` | how long Ollama keeps the model in RAM |
| `OLLAMA_WARMUP_TIMEOUT` | `300` | budget for the model preload at startup |
| `MAX_UPLOAD_MB` | `15` | upload size limit |
| `MAX_PAGES` | `40` | pages analysed per document |
| `TESSERACT_CMD` | *(empty)* | full path to `tesseract.exe` on Windows |
| `OCR_LANGS` | `eng+mal` | OCR languages |
| `ESPEAK_CMD` | *(auto-detected)* | path to `espeak-ng` for offline speech |
| `TESSDATA_DIR` | `<project>/tessdata` if present | language packs folder |
| `OCR_MAX_PAGES` | `8` | image-only pages sent to OCR per document |
| `OCR_DPI` | `200` | render resolution for OCR |
| `OCR_MAX_IMAGE_PX` | `2200` | oversized images are downscaled to this |
| `MAX_EXPLAINED_CLAUSES` | `6` | clauses explained in the one batched request |
| `CLAUSE_TOKEN_BUDGET` | `170` | output tokens per clause; lower is faster |
| `CLAUSE_TOKEN_BUDGET_ML` | `340` | Malayalam needs more tokens per sentence |
| `MAX_EXPLAINED_CLAUSES_ML` | `3` | fewer clauses on the slower Malayalam model |
| `MAX_CLAUSE_CHARS` | `700` | characters sent per clause |
| `MAX_QA_CONTEXT_CHARS` | `3500` | characters of context sent per question |
| `CORS_ORIGINS` | localhost dev ports | allowed browser origins |
| `ENABLE_API_DOCS` | `false` | serve the interactive schema at `/docs` |

---

## Running it

Two terminals.

**Terminal 1 — backend:**

```bash
cd backend
# activate the venv first if it is not active
uvicorn main:app --reload --port 8000
```

**Terminal 2 — frontend:**

```bash
cd frontend
npm run dev
```

Open <http://localhost:5173>.

> Use `localhost`, not `127.0.0.1` — Vite binds the hostname `localhost` only.

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`, so the browser only
ever talks to one origin.

Check the backend by itself at <http://localhost:8000/api/health>, or read the
auto-generated API docs at <http://localhost:8000/docs> once you set
`ENABLE_API_DOCS=true` in `.env`. They are off by default.

The status pill in the top right of the app shows the real state of Ollama and
OCR. Click it for the full message and the exact commands to fix whatever is
missing.

### Production build of the frontend

```bash
cd frontend
npm run build
npm run preview
```

---

## Demo documents

Four synthetic documents live in `demo/`, with every name, amount and date
invented. They are labelled as synthetic demo documents inside the PDF itself.

```
demo/demo_rental_agreement.pdf     rent, deposit, 11 months, lock-in,
                                   auto-renewal, late fee, deposit deduction,
                                   notice period, one-sided clauses
demo/demo_loan_agreement.pdf       loan amount, floating interest, EMI,
                                   processing fee, penal interest, foreclosure
demo/demo_hospital_bill.pdf        charge heads, total payable, due date,
                                   late payment charge, claim window
demo/demo_government_notice.pdf    issuing authority, reference number,
                                   demand, reply deadline, hearing date
demo/demo_malayalam_notice.png     a Malayalam rent notice rendered as an
                                   image, for the OCR + Malayalam rule path
demo/demo_handwritten_note.png     handwriting-style note, to show honestly
                                   where OCR starts to fail
```

Regenerate them at any time:

```bash
python demo/make_demo_docs.py
```

The rental agreement is the best one to demonstrate: it triggers nine clause
categories and has a real auto-renewal trap.

---

## Testing

```bash
cd backend
python -m pytest
```

118 tests covering:

- PDF text extraction, hyphen rejoining, paragraph preservation, page numbering
- sentence and clause segmentation, including `Rs.` and numbered clauses
- classification of all four document types, plus uncertain and unrelated text
- fact extraction, including values read from the right part of a sentence
- ambiguous dates marked uncertain rather than resolved silently
- every one of the 12 clause categories
- **false positives**: negative phrases that veto a match, isolated keywords in
  the wrong context, weak deadline wording with no date
- the Ollama integration against a **stub Ollama server** on a spare port: status
  probe, missing-model message, batching (three clauses, one HTTP call), JSON
  recovery from chatty replies, invalid JSON falling back to rules
- prompt injection inside a document not escaping its fenced block
- the Ollama-unavailable path for clauses, summary and Q&A
- a question with no support in the document never reaching the model
- real OCR: a scanned PDF with no text layer, a photo upload, the OCR page
  budget, a blank image, an unreadable image, and language packs filtered to
  what is installed
- the Malayalam script guard: a reply in another language is discarded, genuine
  Malayalam is accepted, English is not script-checked
- Malayalam documents: chillu folding, "18,500 രൂപ" amounts, "11 മാസം"
  durations, classification, facts and clauses, plus real Malayalam OCR
- invalid uploads: wrong extension, wrong magic bytes, empty file, oversized
  file, corrupt PDF, image upload with no OCR installed
- all API endpoints, and `.ics` output against RFC 5545 line folding and escaping

The Ollama tests use a stub server, so the suite passes whether or not Ollama is
installed. The OCR tests build a genuine scanned PDF (the demo agreement rendered
to images, with the text layer verified absent) and are skipped automatically
when Tesseract is missing. A full run takes about 35 seconds.

**On accuracy:** no accuracy percentage is claimed anywhere in this project. The
tests show that each rule fires on wording it should fire on and stays quiet on
wording it should not. Measuring real-world accuracy would need a labelled corpus
of actual documents, which this MVP does not have.




---

## Audio, and why Malayalam needs an extra step

Speech uses the browser's own voices first. The catch: **Windows ships no
Malayalam text-to-speech voice.** On the development machine the only installed
voices were:

```
Microsoft David Desktop  | en-US
Microsoft Zira Desktop   | en-US
```

So a Malayalam explanation had nothing to read it with. The first version
quietly read Malayalam text aloud in an English voice, which sounds like
nonsense and is exactly the kind of silent wrongness this project avoids
elsewhere.

What happens now:

1. If the browser has a real voice for the language, it is used.
2. If it does not, Doc Decode calls its own `/api/tts`, which runs **eSpeak NG
   locally**. Robotic, but correct, offline, and nothing leaves the machine.
3. If eSpeak NG is not installed either, the Read aloud button is **disabled**
   for that language with a note saying why, rather than speaking it wrongly.

Install the offline engine (one command, about 10 MB):

```powershell
winget install eSpeak-NG.eSpeak-NG
```

Restart the backend afterwards. The status pill then shows **Offline voice:
available**, and Malayalam audio works with no internet connection.

A **voice selector** appears next to the language toggle whenever more than one
voice exists for the current language, so you can pick a specific one.

### A privacy note on browser voices

Some browsers, notably Edge, offer "Online (Natural)" voices that send the text
to the vendor's servers to be spoken. The Web Speech API does not let a page
tell those apart from local ones. If that matters to you, choose a local voice
in the selector or install eSpeak NG and let the offline path handle it.


---

## What it can and cannot read

Two questions worth answering before a demo.

### A PDF downloaded from the internet

**Yes, if it has a real text layer** — which most official PDFs do (bank
statements, government notices, e-bills, agreements emailed to you). Nothing
about the pipeline is tuned to the bundled demo files.

Tested on a sanction letter written in a completely different style from the
demo documents, with vocabulary the rules were never written against:

| | |
| --- | --- |
| Classified | `loan_agreement`, confident |
| Facts read | loan amount `Rs. 32,00,000`, interest `8.75%`, EMI `Rs. 28,410`, tenure `240 months`, processing fee `0.50%`, first EMI due `07/03/2026` |
| Clauses flagged | 8, including the "sole discretion" withdrawal right and the 24% default interest |
| Deadlines | 3, correctly ranked |
| Time | 2.2 s (rules only) |

What limits accuracy:

- **A scanned PDF** (an image with no text layer) goes through OCR, and OCR
  quality then caps everything downstream.
- **Unusual phrasing** can miss a rule. The rules cover common Indian legal and
  financial wording; a clause phrased oddly may not be flagged. Nothing is
  invented to compensate — a field with no match reads "Not found".
- **Every fact shows its source sentence and page**, so you can check any value
  in seconds rather than trusting it.

### Handwritten notes

**No, not reliably.** Tesseract is trained on printed text. It has no
handwriting model, and real handwriting — joined-up letters, varying slant,
ballpoint on lined paper — is a different recognition problem.

Measured with two handwriting-style *fonts*, which are far cleaner and more
regular than any real hand:

| Rendering | Values recovered | Result |
| --- | --- | --- |
| Ink Free (print-like) | 5 / 5 | all facts correct |
| Lucida Handwriting (cursive) | 4 / 5 | `Rs.` read as `Ry.`, `months` as `monthy`, and one fact came out as a run-on string |

Even on neat synthetic handwriting the cursive case already degrades. Genuine
handwriting usually does far worse. Treat handwriting as **out of scope**:
the honest demo line is "printed and scanned documents, not handwriting".

Handwriting would need a different engine (a trained HTR model such as
TrOCR), which is a separate project, not a setting to switch on. The app does
not pretend otherwise: when OCR is used it warns that characters can be
misread and shows you the extracted text so you can see what it actually read.

`demo/demo_handwritten_note.png` is included so you can show this honestly
rather than being surprised by it.


---

## Choosing a model for your GPU

**This is the single biggest factor in how fast Doc Decode feels.** Ollama puts
as much of a model in VRAM as fits and runs the rest on the CPU. A model that
spills is several times slower, with no warning anywhere in the UI.

Check what is happening:

```bash
curl http://localhost:11434/api/ps
nvidia-smi --query-gpu=name,memory.total --format=csv
```

In the `/api/ps` output, compare `size_vram` with `size`. If they match, the
model is entirely on the GPU. If `size_vram` is much smaller, part of the model
is on the CPU and generation will crawl.

Measured on the development machine (RTX 3050 Laptop, **4 GB VRAM**):

| Model | Size | Fits in 4 GB VRAM | Full analysis |
| --- | --- | --- | --- |
| `qwen2.5:3b` | 2.2 GB | **yes, 100% GPU** | **17 s** |
| `gemma2:9b` | 7.1 GB | no, only 31% | 214 s |

Same document, same code: **12x** difference, purely from whether the model fits.

**So Doc Decode lets you set two models.** `OLLAMA_MODEL` handles English and
should be one that fits your VRAM. `OLLAMA_MODEL_ML` is loaded only when the
user switches to Malayalam, where a bigger multilingual model is worth the wait:

```
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_MODEL_ML=gemma2:9b
```

Set `OLLAMA_MODEL_ML` empty to use one model for both. Switching language makes
Ollama swap models, so the first Malayalam request pays a load; the UI says so.

Rough guide: a Q4 model needs roughly `parameters x 0.7 GB` of VRAM, plus about
1 GB of headroom. With 4 GB, stay at 3B or below for the interactive path. If
you have 8 GB or more, put the larger model in `OLLAMA_MODEL` too.

If everything is slow regardless, lower `MAX_EXPLAINED_CLAUSES` and
`CLAUSE_TOKEN_BUDGET`: generation time is roughly proportional to their product.



### Why a reply that is cut off is not retried

If the token budget runs out mid-JSON, the reply is unparseable. Regenerating
it truncates at exactly the same place, so a retry costs a second full
generation and fails identically — measured here at **462 s for zero usable
clauses** before this was fixed.

Doc Decode instead salvages every complete `{...}` object from the truncated
reply, keeps those clauses, falls back to rule notes for the rest, and says in
the warnings that the reply was cut short. One generation, partial success,
honest about it.

Malayalam needs roughly twice the tokens of English for the same sentence,
which is why `CLAUSE_TOKEN_BUDGET_ML` is higher while
`MAX_EXPLAINED_CLAUSES_ML` is lower.


---

## Measured on a real machine

Windows 11, `qwen2.5:3b` (Q4_K_M, 1.9 GB), Tesseract 5.5.3, CPU inference.
These are observed numbers from this project, not estimates.

| Step | Time |
| --- | --- |
| Rule-only analysis (no AI) | **4-5 ms** |
| Full analysis, `qwen2.5:3b` warm (100% GPU) | **17 s** |
| Full analysis, `gemma2:9b` warm (31% GPU, 4 GB card) | 214 s |
| Full analysis, model cold | **>120 s** — the model load alone, not generation |
| Clause batch, 8 clauses warm | 13.6 s (771 generated tokens, ~57 tok/s) |
| Scanned 2-page PDF, OCR | 5.3 s |
| Single photo (PNG), OCR | 1.0 s |
| Q&A question, warm | ~6 s |

**Why the backend preloads the model.** A cold load blew past the old 120 s
timeout and every clause fell back to rule notes, which looks broken in a demo.
The backend now loads the model in a background thread at startup and sets
`keep_alive=30m`, and the default timeout is 240 s. Start the backend a minute
before you present.

**OCR accuracy.** The demo agreement rendered to images and run through OCR gave
2915 characters against 2892 from the real text layer, and every extracted fact
matched: rent `Rs. 18,500`, deposit `Rs. 1,10,000`, end date `28th February 2026`.
That is clean rendered text, not a phone photo of a crumpled page — expect worse
from the latter.

**Malayalam.** `qwen2.5:3b` answered Malayalam requests in **Chinese**. The app
checks whether the reply is actually Malayalam script and discards it if not,
showing rule-based notes and a warning instead of passing another language off
as a translation. `gemma2:9b` does write real Malayalam once the prompt names
the script explicitly, which is why the prompt now carries a LANGUAGE RULE line
with a sample sentence.

Because the bigger model is slow on a small card, Malayalam is configured
separately and loaded only when the user asks for it — see
[Choosing a model for your GPU](#choosing-a-model-for-your-gpu). English
explanations from `qwen2.5:3b` are good and fast.


### Malayalam document support

Malayalam is handled at two separate levels, and they fail independently:

| Level | Needs | State here |
| --- | --- | --- |
| Reading a Malayalam scan (OCR) | `mal.traineddata` | **works** |
| Finding facts and clauses in Malayalam | the rule engine | **works** |
| Explaining a clause *in* Malayalam | a multilingual LLM | needs a bigger model |

The rule engine carries Malayalam vocabulary alongside the English terms, so a
Malayalam rental notice is classified and mined for facts without any LLM
involvement. Three details made that work:

- **Chillu folding.** Six Malayalam consonants have a word-final form with its
  own code point (ർ) *and* an equivalent consonant + virama spelling (ര്). OCR
  and typed text disagree about which to emit, so both are folded to one shape
  before any keyword match.
- **Amounts are suffixed.** Malayalam writes `18,500 രൂപ`, not `Rs. 18,500`. The
  value is reported the way the document writes it rather than relabelled.
- **Durations are suffixed too**: `11 മാസം` is parsed as 11 months.

Measured on the demo notice: OCR read every amount correctly (`18,500`,
`1,10,000`, `250`) and the rules recovered the rent, the duration and the
penalty. Complex conjuncts are where OCR slips — `സെക്യൂരിറ്റി` came back as
`സകെ്യൊരിറ്റി`, so the deposit line was missed. On clean Malayalam text (a PDF
with a real text layer rather than a scan) all six facts are found. That gap is
OCR accuracy, not the rules.


---

## API reference

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | backend, Ollama and OCR state, model availability, limits |
| `POST` | `/api/analyze` | multipart upload; returns the full structured analysis |
| `POST` | `/api/explain` | re-explain known clauses (language switch, AI retry) |
| `POST` | `/api/ask` | a grounded answer plus evidence sentences |
| `POST` | `/api/calendar` | `.ics` file for the deadlines the user ticked |
| `GET` | `/api/rules` | what the rule engine checks, for demonstrations |

`/api/explain` exists so switching to Malayalam, or retrying after you start
Ollama, does not re-upload or re-extract the document.

---

## Privacy and security

- The uploaded file is held in memory for one request and dropped when the
  request ends. This app does not write your document to disk, so there is no
  stored copy to clean up.
- There is no database and no document history. Reload the page and the analysis
  is gone. That is deliberate.
- Document text is sent to the Ollama model at your own `localhost` address.
  Nothing is sent to any external service. There is no cloud AI call anywhere in
  the codebase and no API key.
- Uploads are validated by extension, declared MIME type **and** magic bytes, so
  a renamed executable is rejected. Nothing uploaded is ever executed.
- The server logs the filename, page count, character count and timings.
  Document text is not logged.
- Document text is treated as untrusted data. It is fenced inside a delimited
  block in the prompt, and the system prompt tells the model to ignore any
  instruction inside that block. A test covers this.
- Audio uses your browser's own speech voices. Depending on your operating
  system, the browser may use an online voice — that is the browser's behaviour,
  not Doc Decode's.

**This is a hackathon MVP, not a hardened product.** There is no authentication,
no encryption at rest and no rate limiting. Do not expose it to a network you do
not control, and do not treat it as a secure document store. Complete security is
not claimed.

---

## Troubleshooting

**"Ollama is not reachable"**
Start it with `ollama serve` (the desktop app does this for you). Confirm with
`curl http://localhost:11434/api/tags`. If Ollama runs on another port, update
`OLLAMA_BASE_URL`.

**"Model X is not installed"**
Run `ollama list` to see what you have, then either `ollama pull <model>` or set
`OLLAMA_MODEL` to a model in that list.

**"The model did not return valid JSON"**
Small models sometimes answer in prose. Doc Decode retries once, tries to recover
a JSON object from the reply, then falls back to rule-based notes and says so.
A larger model usually fixes it.

**Malayalam is very slow**
Expected if the Malayalam model does not fit your VRAM. It is loaded only when
you switch language, and it explains fewer clauses
(`MAX_EXPLAINED_CLAUSES_ML`). To speed it up, either use a smaller multilingual
model in `OLLAMA_MODEL_ML`, or lower `MAX_EXPLAINED_CLAUSES_ML` to 2. English
stays fast either way because it uses a different model.

**Explanations time out**
The backend preloads the model at startup and keeps it in RAM for 30 minutes, so
this should be rare. If it still happens, raise `OLLAMA_TIMEOUT`, lower
`MAX_EXPLAINED_CLAUSES`, or use a smaller model. A cold load of a 2 GB model can
take over two minutes by itself, which is exactly what the preload exists to move
out of your first upload.

**"Tesseract OCR was not found"**
Only matters for scans and photos. Install Tesseract and, on Windows, set
`TESSERACT_CMD` to the full path of `tesseract.exe`. Text-based PDFs need no OCR.

**OCR reads Malayalam as nonsense**
Install the Malayalam language data and set `OCR_LANGS=eng+mal`. The health badge
shows whether Doc Decode can see it.

**"The backend is not reachable"**
Make sure `uvicorn` is running on port 8000 and that you opened the frontend on
`http://localhost:5173`.

**The page is blank after `npm run dev`**
Make sure `npm install` finished, and approve the esbuild install script as shown
above.

**Malayalam explanations come back as rule-based notes**
The configured model cannot write Malayalam. See *Measured on a real machine*
below. Set `OLLAMA_MODEL` to a larger multilingual model and restart the backend.

**No Malayalam audio**
Windows has no Malayalam TTS voice, so the browser has nothing to read it with.
Install the offline engine with `winget install eSpeak-NG.eSpeak-NG` and restart
the backend. Until then the Read aloud button is disabled for Malayalam rather
than speaking it in an English voice. See
[Audio](#audio-and-why-malayalam-needs-an-extra-step).

**A date looks wrong**
`12/03/2025` is read day-first, which is the Indian convention, and such dates
are marked "uncertain" in the UI. Check the source sentence shown beside the fact.

---

## Limitations

Worth saying out loud, including to judges:

- **Rules, not understanding.** The clause detector matches wording. It will miss
  an unusual clause phrased in an unusual way, and it can flag a harmless
  sentence. Every flag shows the original text so you can judge it yourself.
- **Attention indicators, not legal judgments.** Nothing here says a clause is
  illegal, void, unenforceable or fraudulent, because this MVP cannot establish
  that. A test asserts that no rule uses those words.
- **Not legal or financial advice.** For a decision that matters, read the
  original document and talk to a qualified lawyer or financial adviser.
- **OCR quality limits everything downstream.** A blurred photo gives bad text,
  and bad text gives bad facts. The UI flags when OCR was used.
- **Handwriting is out of scope.** Tesseract reads printed text; it has no
  handwriting model. See [What it can and cannot read](#what-it-can-and-cannot-read).
- **Speed depends on whether your model fits in VRAM**, not on the document. A
  model that spills to CPU is several times slower. See
  [Choosing a model for your GPU](#choosing-a-model-for-your-gpu).
- **Malayalam output depends entirely on the model, and small models fail at
  it.** Measured here: `qwen2.5:3b` answered Malayalam requests *in Chinese*.
  Doc Decode now checks the script of what comes back and discards a reply that
  is not Malayalam rather than presenting it as the translation. It cannot judge
  whether grammatical-looking Malayalam is actually *good*, so treat Malayalam
  output from a small model as a draft and keep English a click away.
- **Document type coverage is four plus "other".** Other documents still get
  generic amount, date and clause rules.
- **Long documents are capped** at `MAX_PAGES` pages and `MAX_EXPLAINED_CLAUSES`
  AI explanations, to keep a laptop demo responsive. Both are configurable, and
  the UI tells you when a cap was hit.
- **Nothing persists.** No history, no saved reports, no accounts.

---

## Licence and disclaimer

Built as a student hackathon project. The demo documents are entirely fictional.

Doc Decode points out wording that deserves attention and explains it in simpler
words. It does not decide whether anything is legal, valid or fair, and it can
miss things. Check the original document before you sign, pay or reply.
