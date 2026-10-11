// Count EQ-Bench "not X, but Y" matches (slop-score stage-1 regexes) per document.
// Usage: node contrast_counts.mjs <texts.json>  -> prints a JSON array of counts
import fs from 'node:fs';
import { extractContrastMatches } from './sources/slop-score/js/contrast-detector.js';
const texts = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const quiet = {}; for (const k of ['log', 'group', 'groupEnd', 'warn', 'error']) { quiet[k] = console[k]; console[k] = () => {}; }
const counts = texts.map(t => extractContrastMatches(t).length);
Object.assign(console, quiet);
console.log(JSON.stringify(counts));
