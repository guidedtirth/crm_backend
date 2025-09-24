const db = require('../db');
const PLATFORM = 'upwork';

function parseStringArray(input) {
  if (Array.isArray(input)) return input.map((x) => String(x).trim()).filter(Boolean);
  if (typeof input === 'string') return input.split(',').map((s) => s.trim()).filter(Boolean);
  return [];
}

function parseRangeString(input) {
  if (!input || typeof input !== 'string') return { min: null, max: null };
  const [a, b] = input.split('-').map((s) => s.trim());
  const min = a === '' || a == null ? null : Number(a);
  const max = b === '' || b == null ? null : Number(b);
  return { min: Number.isFinite(min) ? min : null, max: Number.isFinite(max) ? max : null };
}

function sanitizeFilters(payload) {
  const NUM = (v, d = null) => (v === null || v === undefined || v === '' ? d : Number(v));
  const BOOL = (v, d = false) => (typeof v === 'boolean' ? v : v === 'true' ? true : v === 'false' ? false : d);
  const STR = (v, d = null) => (typeof v === 'string' && v.trim() ? v.trim() : d);

  const categoryIds = parseStringArray(payload.categoryIds_any);

  // New inputs: budget as ["min-max"], hourlyRate as "min-max"
  const budgetArr = Array.isArray(payload.budget) ? payload.budget : [];
  const budgetParsed = budgetArr.length ? parseRangeString(String(budgetArr[0])) : { min: null, max: null };
  const hourlyParsed = payload.hourlyRate ? parseRangeString(String(payload.hourlyRate)) : { min: null, max: null };

  // Build workload strictly per rules
  const wantPart = !!payload.workload_part_time; // from UI checkbox (less than 30)
  const wantFull = !!payload.workload_full_time; // from UI checkbox (30+)
  const wl = [];
  if (wantPart) { wl.push('as_needed', 'part_time'); }
  if (wantFull) { wl.push('full_time'); }

  const result = {
    category_ids: categoryIds,
    workload: wl,
    verified_payment_only: BOOL(payload.verifiedPaymentOnly_eq, false),
    client_hires_min: NUM(payload.clientHires_min, null),
    client_hires_max: NUM(payload.clientHires_max, null),
    hourly_rate_min: hourlyParsed.min ?? NUM(payload.hourlyRate_min, null),
    hourly_rate_max: hourlyParsed.max ?? NUM(payload.hourlyRate_max, null),
    budget_min: budgetParsed.min ?? NUM(payload.budget_min, null),
    budget_max: budgetParsed.max ?? NUM(payload.budget_max, null),
    proposal_min: NUM(payload.proposal_min, null),
    proposal_max: NUM(payload.proposal_max, null),
    experience_level: STR(payload.experienceLevel_eq, null),
  };

  // Basic validations
  const rangeOk = (lo, hi) => (lo == null || hi == null ? true : Number(lo) <= Number(hi));
  if (!rangeOk(result.client_hires_min, result.client_hires_max)) throw new Error('client_hires_min must be <= client_hires_max');
  if (!rangeOk(result.hourly_rate_min, result.hourly_rate_max)) throw new Error('hourly_rate_min must be <= hourly_rate_max');
  if (!rangeOk(result.budget_min, result.budget_max)) throw new Error('budget_min must be <= budget_max');
  if (!rangeOk(result.proposal_min, result.proposal_max)) throw new Error('proposal_min must be <= proposal_max');

  return result;
}

async function getFilters(req, res) {
  try {
    const companyId = req.user?.company_id;
    if (!companyId) return res.status(401).json({ error: 'Missing company scope' });
    const scope = String(req.query.scope || 'company').toLowerCase();
    const profileId = req.query.profileId || null;
    let r;
    if (scope === 'profile' && profileId) {
      r = await db.query('SELECT * FROM job_filters WHERE platform = $1 AND company_id = $2 AND profile_id = $3 LIMIT 1', [PLATFORM, companyId, profileId]);
    } else {
      r = await db.query('SELECT * FROM job_filters WHERE platform = $1 AND company_id = $2 AND profile_id IS NULL LIMIT 1', [PLATFORM, companyId]);
    }
    if (r.rows.length === 0) {
      return res.json({
        scope,
        active: false,
        categoryIds_any: [],
        workload_part_time: false,
        workload_full_time: false,
        verifiedPaymentOnly_eq: false,
        clientHires_min: null,
        clientHires_max: null,
        hourlyRate_min: null,
        hourlyRate_max: null,
        budget_min: null,
        budget_max: null,
        proposal_min: null,
        proposal_max: null,
        experienceLevel_eq: null,
        updated_at: null,
      });
    }
    const row = r.rows[0];
    return res.json({
      scope,
      active: !!row.active,
      categoryIds_any: (row.category_ids || []).map((v) => String(v)),
      workload_part_time: Array.isArray(row.workload) ? row.workload.includes('part_time') || row.workload.includes('as_needed') : false,
      workload_full_time: Array.isArray(row.workload) ? row.workload.includes('full_time') : false,
      verifiedPaymentOnly_eq: row.verified_payment_only,
      clientHires_min: row.client_hires_min ?? null,
      clientHires_max: row.client_hires_max ?? null,
      hourlyRate_min: row.hourly_rate_min ?? null,
      hourlyRate_max: row.hourly_rate_max ?? null,
      budget_min: row.budget_min ?? null,
      budget_max: row.budget_max ?? null,
      proposal_min: row.proposal_min ?? null,
      proposal_max: row.proposal_max ?? null,
      experienceLevel_eq: row.experience_level,
      updated_at: row.updated_at,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}

async function saveFilters(req, res) {
  try {
    const companyId = req.user?.company_id;
    if (!companyId) return res.status(401).json({ error: 'Missing company scope' });
    const scope = String(req.body.scope || 'company').toLowerCase();
    const active = req.body.active === true || req.body.active === 'true';
    const profileId = req.body.profileId || null;
    const f = sanitizeFilters(req.body || {});

    if (scope === 'profile') {
      if (!profileId) return res.status(400).json({ error: 'profileId required for profile scope' });
      const own = await db.query('SELECT 1 FROM profiles WHERE id = $1 AND company_id = $2', [profileId, companyId]);
      if (own.rows.length === 0) return res.status(404).json({ error: 'Profile not found' });
      await db.query(
        `INSERT INTO job_filters (
          platform, company_id, profile_id, active,
          category_ids, workload, verified_payment_only,
          client_hires_min, client_hires_max,
          hourly_rate_min, hourly_rate_max,
          budget_min, budget_max,
          proposal_min, proposal_max,
          experience_level, updated_at
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,NOW())
        ON CONFLICT (platform, company_id, profile_id)
        DO UPDATE SET active = EXCLUDED.active,
          category_ids = EXCLUDED.category_ids,
          workload = EXCLUDED.workload,
          verified_payment_only = EXCLUDED.verified_payment_only,
          client_hires_min = EXCLUDED.client_hires_min,
          client_hires_max = EXCLUDED.client_hires_max,
          hourly_rate_min = EXCLUDED.hourly_rate_min,
          hourly_rate_max = EXCLUDED.hourly_rate_max,
          budget_min = EXCLUDED.budget_min,
          budget_max = EXCLUDED.budget_max,
          proposal_min = EXCLUDED.proposal_min,
          proposal_max = EXCLUDED.proposal_max,
          experience_level = EXCLUDED.experience_level,
          updated_at = NOW()`,
        [
          PLATFORM, companyId, profileId, active,
          f.category_ids, f.workload, f.verified_payment_only,
          f.client_hires_min, f.client_hires_max,
          f.hourly_rate_min, f.hourly_rate_max,
          f.budget_min, f.budget_max,
          f.proposal_min, f.proposal_max,
          f.experience_level
        ]
      );
    } else {
      // Company default: use update-then-insert to avoid relying on a partial unique constraint name
      const upd = await db.query(
        `UPDATE job_filters SET
           active = $3,
           category_ids = $4,
           workload = $5,
           verified_payment_only = $6,
           client_hires_min = $7,
           client_hires_max = $8,
           hourly_rate_min = $9,
           hourly_rate_max = $10,
           budget_min = $11,
           budget_max = $12,
           proposal_min = $13,
           proposal_max = $14,
           experience_level = $15,
           updated_at = NOW()
         WHERE platform = $1 AND company_id = $2 AND profile_id IS NULL`,
        [
          PLATFORM, companyId, active,
          f.category_ids, f.workload, f.verified_payment_only,
          f.client_hires_min, f.client_hires_max,
          f.hourly_rate_min, f.hourly_rate_max,
          f.budget_min, f.budget_max,
          f.proposal_min, f.proposal_max,
          f.experience_level
        ]
      );
      if (upd.rowCount === 0) {
        await db.query(
          `INSERT INTO job_filters (
             platform, company_id, profile_id, active,
             category_ids, workload, verified_payment_only,
             client_hires_min, client_hires_max,
             hourly_rate_min, hourly_rate_max,
             budget_min, budget_max,
             proposal_min, proposal_max,
             experience_level, updated_at
           ) VALUES ($1,$2,NULL,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,NOW())`,
          [
            PLATFORM, companyId, active,
            f.category_ids, f.workload, f.verified_payment_only,
            f.client_hires_min, f.client_hires_max,
            f.hourly_rate_min, f.hourly_rate_max,
            f.budget_min, f.budget_max,
            f.proposal_min, f.proposal_max,
            f.experience_level
          ]
        );
      }
    }
    return res.json({ ok: true });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
}

module.exports = { getFilters, saveFilters };


