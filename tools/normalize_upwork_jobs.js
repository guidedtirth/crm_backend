// One-time normalizer: rewrite upwork_jobs.job_data to canonical storage shape
// Usage: node tools/normalize_upwork_jobs.js

const db = require('../db');
const { canonicalizeJobNode } = require('../platforms/upwork/utils');

async function main() {
  try {
    console.log('Loading rows…');
    const { rows } = await db.query('SELECT id, job_data FROM upwork_jobs ORDER BY id ASC');
    let updated = 0;
    for (const r of rows) {
      const original = r.job_data;
      const canonical = canonicalizeJobNode(original);
      // Skip if already canonical (heuristic: no nested job, has title/description fields)
      const needsUpdate = !!original?.job || !('title' in original) || !('description' in original);
      if (!needsUpdate) continue;
      await db.query('UPDATE upwork_jobs SET job_data = $1 WHERE id = $2', [canonical, r.id]);
      updated += 1;
    }
    console.log(`Normalized ${updated} row(s).`);
    process.exit(0);
  } catch (e) {
    console.error('Normalization failed:', e.message);
    process.exit(1);
  }
}

main();


