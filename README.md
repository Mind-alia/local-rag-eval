# local-rag-eval

[![CI](https://github.com/Mind-alia/local-rag-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/Mind-alia/local-rag-eval/actions/workflows/ci.yml)

A small bench in plain Python (standard library only) that checks a local RAG setup. Does a local
model answer questions about a set of Markdown files with the right facts and the right
citations? Does it say `JE NE SAIS PAS` (I don't know) when the files do not hold the answer?

This is the code of the bench behind my note *Zero exact answers on the first run* (« 0 réponse
exacte au premier essai »). The corpus and questions it was measured on are private and are not
included; an invented demo corpus takes their place.

## What it does

- **Hybrid search.** Each Markdown file is cut at its headings into passages of at most 800
  characters, with 100 characters of overlap. A question is searched with BM25 (SQLite FTS5,
  accents ignored) and with embeddings (`qwen3-embedding:0.6b`, cosine similarity). Reciprocal
  rank fusion (RRF, `weight / (60 + rank)`) merges the two rankings.
- **Local model.** The best passages go to `qwen3:8b` through Ollama, at temperature 0. The only
  network calls go to Ollama on `127.0.0.1:11434`.
- **Citations mapped by code.** The prompt numbers the excerpts `[E1]`, `[E2]`… (five by default)
  and asks the model to cite only those numbers. The code maps each number back to its file.
- **Scoring.** Each answer is flagged:
  - *exact*: all the expected keywords, and a citation of the expected file (full path: two files
    with the same name are not the same file);
  - *right, badly cited*: all the expected keywords, but no citation of the expected file;
  - *correct abstention*: exactly `JE NE SAIS PAS`, on a question whose answer is not in the corpus;
  - *invention*: an answer to such a question, a missing or unknown citation, or citations of
    other files only, without all the keywords.

  Retrieval is measured by recall@5, by file and by evidence passage.
- **Rescoring without the model.** Each results file keeps every answer and the excerpts the model
  saw. `--rescore` grades them again with the current rules and annotations, makes no model call,
  and writes a `-rescored.json` copy next to the original, which stays untouched.

## Run it

Python 3.11 or later, with the FTS5 extension in `sqlite3` (common builds have it). Nothing to
install.

```sh
python3 -m unittest -v
```

The 17 tests need no model. One fails if the old citation template comes back into the prompt;
another makes any model call fail and checks that rescoring still works without touching the
original file.

The bench itself needs [Ollama](https://ollama.com) running on the same machine, with both models:

```sh
ollama pull qwen3-embedding:0.6b
ollama pull qwen3:8b
python3 eval.py --mode retrieval                    # search only: recall@5, no chat model
python3 eval.py                                     # search, answers and scores
python3 eval.py --rescore results-<timestamp>.json  # grade saved answers again, offline
```

| Option | Default | Effect |
|---|---|---|
| `--mode` | `all` | `retrieval` skips the chat model; `answer` and `all` also answer and score |
| `--limit N` | all | first N questions only |
| `--embed-model`, `--chat-model` | `qwen3-embedding:0.6b`, `qwen3:8b` | Ollama models |
| `--bm25-weight` | `1.0` | weight of BM25 in the fusion; embeddings stay at `1.0` |
| `--no-stopwords` | off | keeps function words in the BM25 query, as the first runs did |
| `--fusion` | `rrf` | `rrf-gated` uses BM25 only if its best passage holds at least two words of the question |
| `--context-k` | `5` | excerpts given to the model; recall is always measured at 5 |
| `--variant NAME` | none | adds `-NAME` to the results file name |

A run writes `results-<UTC timestamp>.json` next to the script and stores embeddings in
`embeddings-cache.json`. Git ignores both.

## Demo corpus

[`demo-corpus/`](demo-corpus/) documents **cagibi**, a command-line tool that does not exist: seven
short pages in French, invented for this repository and listed in [`corpus.txt`](corpus.txt).
[`questions.json`](questions.json) uses the original format: 7 questions answered in the pages
(5 in French, 2 in English) and 3 traps whose only right answer is `JE NE SAIS PAS`. Two pages are
both named `configuration.md`, on purpose. The demo is there to make the bench runnable; its
scores are not part of the story below.

## The story

The first run, on 17 October 2026, scored 0 exact answers out of 20, with 19 inventions. Only the
abstentions held: 5 out of 5.

The answers said otherwise. The prompt gave the citation template `[fichier#section]`
(file#section). The model copied it word for word in 12 answers; in 7 others it wrote a short file
name or kept the word « fichier ». No citation pointed to one precise document, and two documents
of the corpus share the same name.

The results file had kept the answers and their excerpts, so I added rescoring and the *right,
badly cited* category. Rescored, the first run still had 0 exact answers, but 16 out of 20 answers
held all the expected keywords. The model had found the facts; the citation format had failed.

The fix is the numbered excerpts described above. The second run, with the same model, questions
and corpus, gave 15 exact answers out of 20. Then I tuned the search:

| Run | Exact, cited | Right, badly cited | Inventions | Per question |
|---|---|---|---|---|
| 1. First run | 0/20 | 16 (rescored) | 19 | 6.8 s |
| 2. Numbered excerpts | 15/20 | 1 | 1 | 5.3 s |
| 3. Stopwords removed, BM25 at 0.5 | 16/20 | 1 | 1 | 4.0 s |
| 4. Eight passages | 16/20 | 2 | 0 | 6.4 s |

`qwen3:8b`, the same 25 questions (20 answerable, 5 traps), 17 October 2026, one run per row.
Correct abstentions: 5 out of 5 in every run.

At equal weight, BM25 dragged the hybrid search down: English questions on French documents,
function words. With stopwords removed and BM25 at 0.5, recall@5 reached 0.95 by file and 0.90 by
passage. Eight passages instead of five removed the last invention, for 2.4 s more per question.

In today's options, runs 2 to 4 used `--no-stopwords`, then `--bm25-weight 0.5`, then
`--bm25-weight 0.5 --context-k 8`. The first prompt is not kept.

## What these numbers do not say

- They come from a **private corpus that is not included**: 24 Markdown documents from my own
  projects (417 passages, then 420, because two documents changed between runs 2 and 3) and 25
  hand-written questions. They cannot be reproduced from this repository.
- **Each setting ran once.**
- 25 hand-picked questions on one corpus do not measure a model's general quality. *Exact* is a
  lexical proxy: a right citation does not prove that the passage supports every sentence.
- **A good score here did not carry over to real use.** I plugged the last setting into an advisor
  that answers my coding agents' questions. It settled **2 of 11 real questions (18 %)**; for the
  other 9, which were about coordination between tasks, it answered that it did not know. The
  advisor stays off by default.

## Changes from the private version

The code is the bench's final version, with three changes:

- `corpus.txt` may list paths relative to the script's folder; the original accepted only absolute
  paths.
- `corpus.txt` and `questions.json` are read as UTF-8 on every system, for the French questions.
- Test fixtures that came from the private corpus were replaced with neutral strings; the tests
  check the same behaviour.
