# ruff: noqa: PT009, PT027 -- Standard-library unittest is required for this spike.
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("model_eval", Path(__file__).with_name("eval.py"))
eval = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eval)


class EvalTests(unittest.TestCase):
    def test_chunking(self):
        text = "# Title\n" + "a" * 1600 + "\n## Other\nlast"
        chunks = eval.chunk_markdown("/x.md", text)
        self.assertEqual([len(c["text"]) for c in chunks[:3]], [800, 800, 200])
        self.assertEqual(chunks[0]["text"][-100:], chunks[1]["text"][:100])
        self.assertEqual(chunks[-1]["section"], "Title > Other")
        self.assertEqual(chunks[-1]["file"], "/x.md")

    def test_bm25(self):
        db = eval.build_bm25(
            [{"text": "éléphant bleu", "section": "Zoo"}, {"text": "red apple", "section": "Fruit"}]
        )
        self.assertEqual(eval.bm25_search(db, "éléphant?"), [0])
        self.assertEqual(eval.bm25_search(db, '" OR *'), [])

    def test_stopwords(self):
        self.assertEqual(
            eval.query_words("What is the rôle de la girafe à x?"), ["rôle", "girafe"]
        )
        db = eval.build_bm25(
            [
                {"text": "what is the de la", "section": "Noise"},
                {"text": "girafe", "section": "Tool"},
            ]
        )
        self.addCleanup(db.close)
        self.assertEqual(eval.bm25_search(db, "What is the girafe?"), [1])
        self.assertEqual(eval.bm25_search(db, "What is the à x?"), [])
        self.assertIn(0, eval.bm25_search(db, "What is the girafe?", stopwords=False))

    def test_weighted_rrf(self):
        self.assertEqual(eval.rrf([0, 1], [1, 0], weights=[0.5, 1]), [1, 0])
        self.assertEqual(eval.rrf([0], [1, 2], weights=[0, 1]), [1, 2])
        with self.assertRaises(ValueError):
            eval.rrf([0], [1], weights=[1])

    def test_gated_rrf(self):
        chunks = [
            {"text": "What is the girafe girafe?", "section": "Noise"},
            {"text": "girafe locale", "section": "Useful"},
        ]
        self.assertEqual(
            eval.fuse([0, 1], [1, 0], chunks, "What is the girafe locale?", fusion="rrf-gated"),
            [1, 0],
        )
        self.assertEqual(
            eval.fuse([1, 0], [0, 1], chunks, "girafe locale", fusion="rrf-gated"),
            eval.rrf([1, 0], [0, 1]),
        )
        self.assertEqual(
            eval.fuse([], [1, 0], chunks, "girafe locale", fusion="rrf-gated"), [1, 0]
        )

    def test_passage_recall(self):
        context = [{"text": "Prefix TOUJOURS\n  noter `--seed` suffix"}]
        self.assertTrue(eval.passage_recall("Toujours noter `--seed`", context))
        self.assertFalse(eval.passage_recall("", context))
        self.assertFalse(eval.passage_recall(None, context))
        self.assertFalse(eval.passage_recall("missing", context))
        self.assertFalse(
            eval.passage_recall("answer", [{"text": "noise"}] * 5 + [{"text": "answer"}])
        )

    def test_q20_same_basename_different_file(self):
        question = {"expected_file": "/alpha/docs/guide.md", "keywords": ["--seed"]}
        context = [
            {"file": "/alpha/docs/guide.md"},
            {"file": "/beta/docs/guide.md"},
        ]
        self.assertTrue(
            eval.score_answer(question, "--seed [E2]", context)["correct_without_good_citation"]
        )
        self.assertTrue(eval.score_answer(question, "--seed [E1]", context)["exact"])

    def test_rrf(self):
        self.assertEqual(eval.rrf([1, 2], [2, 3])[0], 2)
        self.assertEqual(eval.rrf([], []), [])

    def setUp(self):
        self.question = {"id": "q1", "expected_file": "/x.md", "keywords": ["blue"]}
        self.context = [
            {"file": "/other.md", "section": "Other", "text": "red"},
            {"file": "/x.md", "section": "Color", "text": "blue"},
        ]

    def test_citation_translation(self):
        self.assertEqual(eval.citations("blue [E2]", self.context), ["/x.md"])
        self.assertEqual(eval.citations("[fichier#section]", self.context), [])
        self.assertEqual(eval.citations("[E0] [E3]", self.context), [None, None])

    def test_correct_answer_with_good_citation(self):
        scores = eval.score_answer(self.question, "Blue [E2] [E1]", self.context)
        self.assertTrue(scores["exact"])
        self.assertFalse(scores["correct_without_good_citation"])
        self.assertFalse(scores["invention"])

    def test_correct_answer_with_wrong_citation(self):
        scores = eval.score_answer(self.question, "Blue [E1]", self.context)
        self.assertFalse(scores["exact"])
        self.assertTrue(scores["correct_without_good_citation"])
        self.assertFalse(scores["invention"])

    def test_correct_abstention(self):
        absent = {"expected_file": None, "keywords": []}
        scores = eval.score_answer(absent, " JE NE SAIS PAS\n", self.context)
        self.assertTrue(scores["correct_abstention"])
        self.assertFalse(scores["invention"])
        self.assertFalse(scores["correct_without_good_citation"])
        self.assertFalse(eval.is_abstention("JE NE SAIS PAS."))

    def test_inventions(self):
        absent = {"expected_file": None, "keywords": []}
        self.assertTrue(eval.score_answer(absent, "blue [E2]", self.context)["invention"])
        for answer in ("blue", "blue [fichier#section]", "blue [E9]", "red [E1]"):
            with self.subTest(answer=answer):
                self.assertTrue(eval.score_answer(self.question, answer, self.context)["invention"])
        self.assertFalse(eval.score_answer(self.question, "red [E2]", self.context)["exact"])

    def test_prompt_uses_numbered_excerpts(self):
        prompt = eval.format_excerpts(self.context)
        self.assertIn("[E2]", prompt)
        self.assertIn("/x.md", prompt)
        self.assertIn("Color", prompt)
        self.assertNotIn("[fichier#section]", eval.SYSTEM)

    def test_rescore_without_ollama_or_corpus(self):
        report = {
            "questions": [
                {
                    "id": "q1",
                    "expected_file": "/x.md",
                    "answer": "blue [E2]",
                    "top5": {"hybrid": self.context},
                    "scores": {"exact": False},
                }
            ],
            "summary": {"exact": 0, "completed": 1},
        }
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            source = Path(directory) / "results.json"
            source.write_text(json.dumps(report))
            questions = Path(directory) / "questions.json"
            questions.write_text(json.dumps([self.question]))
            with (
                patch.object(eval, "BASE", Path(directory)),
                patch.object(
                    eval, "ollama", side_effect=AssertionError("Ollama must not be called")
                ),
                patch("sys.argv", ["eval.py", "--rescore", str(source)]),
            ):
                eval.main()
            rescored = json.loads(source.with_name("results-rescored.json").read_text())
            self.assertTrue(rescored["questions"][0]["scores"]["exact"])
            self.assertEqual(rescored["summary"]["exact"], 1)
            self.assertEqual(rescored["summary"]["correct_without_good_citation"], 0)
            self.assertEqual(json.loads(source.read_text()), report)

    def test_retrieval_report_and_context_options(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            base = Path(directory)
            corpus = base / "sample.md"
            corpus.write_text("# One\nBlue answer\n# Two\nOther answer")
            (base / "corpus.txt").write_text(str(corpus) + "\n")
            (base / "questions.json").write_text(
                json.dumps(
                    [
                        {
                            "id": "q1",
                            "question": "What is blue?",
                            "expected_file": str(corpus),
                            "keywords": ["blue"],
                            "evidence": "BLUE   answer",
                        },
                        {
                            "id": "q2",
                            "question": "Unknown",
                            "expected_file": None,
                            "keywords": [],
                            "evidence": None,
                        },
                    ]
                )
            )
            with (
                patch.object(eval, "BASE", base),
                patch.object(eval, "embed", return_value=[1.0]),
                patch.object(eval, "ollama", side_effect=AssertionError("No chat in retrieval")),
                patch(
                    "sys.argv",
                    [
                        "eval.py",
                        "--mode",
                        "retrieval",
                        "--context-k",
                        "1",
                        "--variant",
                        "gated",
                        "--fusion",
                        "rrf-gated",
                        "--bm25-weight",
                        "0.5",
                    ],
                ),
            ):
                eval.main()
            report = json.loads(next(base.glob("results-*-gated.json")).read_text())
            self.assertTrue(report["complete"])
            self.assertEqual(report["summary"]["answerable"], 1)
            self.assertEqual(report["summary"]["passage_recall_at_5"]["hybrid"], 1.0)
            self.assertEqual(len(report["questions"][0]["context"]), 1)
            self.assertEqual(len(report["questions"][0]["top5"]["hybrid"]), 2)

    def test_cosine(self):
        self.assertAlmostEqual(eval.cosine([1, 0], [1, 0]), 1)
        self.assertEqual(eval.cosine([0, 0], [1, 0]), 0)
        with self.assertRaises(ValueError):
            eval.cosine([1], [1, 2])


if __name__ == "__main__":
    unittest.main()
