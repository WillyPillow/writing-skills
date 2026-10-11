// Claude Code workflow that generated data/llm_corpus_skill/: the 40 test topics, written by each model
// while following the technical-writing skill. Run it with the Workflow tool, passing
// args {"dir": "<absolute path of this directory>", "skill": "<absolute path of technical-writing/SKILL.md>",
// "out": "<corpus directory under data/, default llm_corpus_skill>"}.
export const meta = {
  name: 'rfc-slop-corpus-skill',
  description: 'Generate 120 PEP/RFC-style docs on the 40 held-out topics with the technical-writing skill (Opus, Sonnet, Haiku)',
  phases: [{ title: 'Generate', detail: '3 models x 4 batches x 10 docs, skill loaded' }],
}
const DIR = args.dir
const SKILL = args.skill
const OUT = args.out || 'llm_corpus_skill'
const MODELS = ['opus', 'sonnet', 'haiku']
const SCHEMA = { type: 'object', properties: { written: { type: 'array', items: { type: 'string' } } }, required: ['written'] }
const jobs = []
for (const m of MODELS) for (let b = 0; b < 4; b++) jobs.push({ m, b })
phase('Generate')
const res = await parallel(jobs.map(({ m, b }) => () => {
  const batch = `${DIR}/data/batches_skill/batch_${String(b).padStart(2, '0')}.md`
  const prompt = `You are generating data for a writing-style study. First read the writing skill at ${SKILL} and follow it for everything you write. Then read the file ${batch}. It lists 10 items, each with an id, a document type, a title and an abstract.

For each item, write the full document (approximately 1200-1500 words) based on the title and abstract, as the author's assistant following that skill. The title and abstract are the author's entire material. No author is available to answer questions or correct a plan: wherever the skill says to ask the author or to wait for corrections, mark the gap in the document with [TODO: ...] instead and continue. Do the skill's review pass yourself before saving. Only output the final document text, with no planning notes and no commentary before or after.

Rules:
- The skill file and the batch file are the ONLY files you may read. Do not read any other file, repository, or web page, do not run searches, and do not invoke any skills through the Skill tool.
- If you recognize the real document, do not try to reproduce it; write your own version.
- Save each document with the Write tool to ${DIR}/data/${OUT}/${m}/<id>.md (use the item's id exactly as the filename stem). The file contains only the document, in Markdown.

Return the list of ids you wrote.`
  return agent(prompt, { label: `${m} batch ${b} (skill)`, phase: 'Generate', model: m, schema: SCHEMA })
}))
const written = res.filter(Boolean).flatMap(r => r.written)
log(`${written.length} documents reported written; ${res.filter(r => !r).length} agents failed`)
return { written: written.length, failed: jobs.filter((j, i) => !res[i]).map(j => `${j.m}:${j.b}`) }
