"""Tests for technical-writing/scripts/check.py. Run: python3 -m unittest discover tests"""

import importlib.util
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "technical-writing", "scripts", "check.py")
spec = importlib.util.spec_from_file_location("check", SCRIPT)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def run_check(name, text, known=(), user_known=(), source=None, builtin=True):
    c = next(c for c in check.CHECKS if c["name"] == name)
    ctx = {
        "user_known": set(user_known),
        "known": set(known) | set(user_known) | (check.BUILTIN_KNOWN if builtin else set()),
        "source_values": check.source_values([source or ""]),
    }
    return [f.message for f in c["func"](check.Document("t", text), ctx)]


def run_main(args, stdin=None):
    out = io.StringIO()
    with redirect_stdout(out):
        check.main(args)
    return out.getvalue()


class NumbersTest(unittest.TestCase):
    SOURCE = "p99 latency 48ms; throughput 40k writes/s; error rate 0.12; 1,500 nodes; 3 replicas"

    def flagged(self, text, minor=False):
        msgs = run_check("numbers-minor" if minor else "numbers", text, source=self.SOURCE)
        return [m.split('"')[1] for m in msgs]

    def test_numbers_in_source_pass(self):
        text = "Latency is 48 ms at p99. We sustain 40,000 writes/s across 1500 nodes."
        self.assertEqual(self.flagged(text), [])

    def test_percent_matches_fraction(self):
        self.assertEqual(self.flagged("The error rate is 12%."), [])

    def test_changed_and_invented_numbers_flagged(self):
        self.assertEqual(self.flagged("Latency is 45 ms, and memory fell by 37.5%."),
                         ["45 ms", "37.5%"])

    def test_labels_dates_versions_and_list_markers_ignored(self):
        text = ("1. See Section 42 and Figure 17, and RFC 2119.\n"
                "Released 2024-03-01 at 14:30 as version 3.13.2.\n")
        self.assertEqual(self.flagged(text), [])

    def test_small_counts_and_years_only_in_minor(self):
        text = "We run 5 shards since 2019, with 3 replicas."
        self.assertEqual(self.flagged(text), [])
        self.assertEqual(self.flagged(text, minor=True), ["5", "2019"])

    def test_number_at_line_start_checked(self):
        self.assertEqual(self.flagged("a latency of\n45 ms at p99.\n3.2 Design\n"), ["45 ms"])

    def test_each_number_reported_once(self):
        self.assertEqual(self.flagged("It took 77 ms. Again 77 ms."), ["77 ms"])

    def test_identifiers_ignored(self):
        self.assertEqual(self.flagged("Use S3 and x86 on IPv6 with ASD-STE100."), [])


class AcronymTest(unittest.TestCase):
    def test_undefined_flagged(self):
        msgs = run_check("acronyms", "The SLO is tight.")
        self.assertEqual(len(msgs), 1)
        self.assertIn("never defined", msgs[0])

    def test_defined_forms_pass(self):
        for text in ("Each service level objective (SLO) is tight. The SLO holds.",
                     "Each SLO (service level objective) is tight.",
                     "SLO stands for service level objective.",
                     "- SLO: service level objective\n\nThe SLO holds."):
            self.assertEqual(run_check("acronyms", text), [], text)

    def test_used_before_definition(self):
        msgs = run_check("acronyms", "The SLO is tight.\n\nA service level objective (SLO) is a target.")
        self.assertEqual(len(msgs), 1)
        self.assertIn("before its definition", msgs[0])

    def test_known_exceptions(self):
        text = "The SLO and the QPS are tight. Our API uses HTTP."
        self.assertEqual(run_check("acronyms", text, user_known={"SLO", "QPS"}), [])
        msgs = run_check("acronyms", text, user_known={"SLO", "QPS"}, builtin=False)
        self.assertEqual(sorted(m.split('"')[1] for m in msgs), ["API", "HTTP"])

    def test_plurals_share_the_definition(self):
        self.assertEqual(run_check("acronyms", "Two service level objectives (SLOs). Each SLO holds."), [])

    def test_code_and_emphasis_skipped(self):
        text = ("Set `TIMEOUT` and MAX_SIZE, call FOO(x), and read $HOME.\n\n"
                "This is NONE of your concern; none at all.\n\nWARNING THIS IS LOUD TEXT\n")
        self.assertEqual(run_check("acronyms", text), [])

    def test_roman_numerals_skipped(self):
        self.assertEqual(run_check("acronyms", "See part II and part IV."), [])

    def test_defines_known(self):
        msgs = run_check("defines-known", "A service level objective (SLO) is a target.",
                         user_known={"SLO"})
        self.assertEqual(len(msgs), 1)


class PhraseChecksTest(unittest.TestCase):
    def assertHits(self, name, text, n=1):
        self.assertEqual(len(run_check(name, text)), n, (name, text))

    def test_todo(self):
        self.assertHits("todo", "Latency is [TODO: get p99]. Owner TBD.", 2)
        self.assertHits("todo", "Nothing to do here.", 0)

    def test_strict_phrases(self):
        self.assertHits("stacked-hedges", "This may potentially fail.")
        self.assertHits("nominalizations", "We performed an optimization of the loop.")
        self.assertHits("stock-phrases", "It is worth noting that caching plays a key role.", 2)
        self.assertHits("stock-phrases", "In today's Python, this works.", 0)
        self.assertHits("vague-importance-clauses",
                        "The cache cut latency, highlighting the importance of locality.")

    def test_unquantified_skips_sentences_with_numbers(self):
        self.assertHits("unquantified-qualities", "The design is scalable.")
        self.assertHits("unquantified-qualities", "It is scalable to 40k writes/s.", 0)
        self.assertHits("unquantified-intensifiers", "This significantly improves latency.")

    def test_reference_phrases(self):
        self.assertHits("stock-vocabulary", "We leverage a robust pipeline.", 2)
        self.assertHits("signposts", "We now turn to the cache.")
        self.assertHits("importance-adverbs", "Notably, the cache is warm.")
        self.assertHits("not-x-but-y", "It is not just fast, but correct.")
        self.assertHits("empty-monitoring", "We will add monitoring.")
        self.assertHits("logic-symbols", "A holds ⇒ B holds.")
        self.assertHits("assume-without-that", "Assume A is a group.")
        self.assertHits("assume-without-that", "Assume that A is a group.", 0)


class SentenceChecksTest(unittest.TestCase):
    def test_sentence_splitting_handles_abbreviations(self):
        doc = check.Document("t", "See Fig. 3 and e.g. the log. Then stop. J. Williams agrees.")
        self.assertEqual([s for _, s in doc.all_sentences()],
                         ["See Fig. 3 and e.g. the log.", "Then stop.", "J. Williams agrees."])

    def test_list_items_split_sentences(self):
        doc = check.Document("t", "Steps\n- first item\n- second item")
        self.assertEqual(len(list(doc.all_sentences())), 3)

    def test_long_sentence(self):
        self.assertEqual(len(run_check("long-sentences", " ".join(["word"] * 26) + ".")), 1)
        self.assertEqual(len(run_check("long-sentences", " ".join(["word"] * 25) + ".")), 0)

    def test_symbol_starts(self):
        text = "We fix a bound. $x$ is positive. n is the number of nodes. I am done."
        self.assertEqual(len(run_check("symbol-starts", text)), 2)

    def test_colon_reveal(self):
        self.assertEqual(len(run_check("colon-reveals", "The answer was always the same: caching.")), 1)
        self.assertEqual(len(run_check("colon-reveals", "The syntax is new: `async with`.")), 0)

    def test_then_thus_hence(self):
        text = "We have a bound. Then it holds. Thus it is small. Hence we are done."
        self.assertEqual(len(run_check("then-thus-hence", text)), 1)

    def test_closing_restatement(self):
        text = "Caches help. They cut latency. They cost memory. Overall, caches help."
        self.assertEqual(len(run_check("closing-restatements", text)), 1)

    def test_term_variants(self):
        msgs = run_check("term-variants", "The write-ahead log and the write ahead log. GitHub vs Github.")
        self.assertEqual(len(msgs), 2)
        self.assertEqual(run_check("term-variants", "NOTE: this is a Note. OK, Ok."), [])

    def test_figure_mentioned_once(self):
        self.assertEqual(len(run_check("figure-mentioned-once", "Figure 1: arch. Figure 2: x. As Figure 1 shows.")), 1)

    def test_noun_cluster(self):
        self.assertEqual(len(run_check("noun-clusters", "Replace the high-pressure fuel pump inlet valve.")), 1)
        self.assertEqual(len(run_check("noun-clusters", "Replace the inlet valve of the fuel pump.")), 0)


class DriverTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.draft = os.path.join(self.dir.name, "draft.txt")
        with open(self.draft, "w") as f:
            f.write("The SLO is a robust 45 ms. [TODO: confirm]\n")
        self.source = os.path.join(self.dir.name, "notes")
        os.mkdir(self.source)
        with open(os.path.join(self.source, "a.txt"), "w") as f:
            f.write("p99 45ms\n")

    def tearDown(self):
        self.dir.cleanup()

    def test_strict_omits_reference_checks(self):
        out = run_main([self.draft, "--source", self.source])
        self.assertIn("-- todo", out)
        self.assertIn("-- acronyms", out)
        self.assertNotIn("-- numbers", out)
        self.assertNotIn("stock-vocabulary", out)
        self.assertNotIn("Reference only", out)
        self.assertIn("does not check substance", out)

    def test_reference_adds_banner_and_checks(self):
        out = run_main([self.draft, "--profile", "reference", "--known", "SLO"])
        self.assertIn("== Reference only ==", out)
        self.assertIn("-- stock-vocabulary", out)
        self.assertNotIn("-- acronyms", out)
        self.assertIn("Not run on", out)

    def test_known_file(self):
        known = os.path.join(self.dir.name, "known.txt")
        with open(known, "w") as f:
            f.write("# team glossary\nSLO  QPS\n")
        out = run_main([self.draft, "--known-file", known])
        self.assertNotIn("-- acronyms", out)

    def test_list_checks(self):
        out = run_main(["--list-checks"])
        for c in check.CHECKS:
            self.assertIn(c["name"], out)


if __name__ == "__main__":
    unittest.main()
