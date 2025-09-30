/**
 * filterAudit.js
 *
 * Standalone audit tool to evaluate how many stored jobs match the current
 * Upwork filters (company default and per-profile) for each company/profile.
 *
 * Parity: Uses the same matching logic as the Upwork pipeline (jobMatchesFilter).
 *
 * Usage (PowerShell):
 *   cd "D:\\New folder\\marcketing backend\\marketing_backend"
 *   node tools\\filterAudit.js                # report for all companies/profiles
 *   node tools\\filterAudit.js --companyId <uuid>
 *   node tools\\filterAudit.js --profileId <uuid>
 *   node tools\\filterAudit.js --limit 10     # limit sample jobs per profile
 */

const dotenv = require('dotenv');
const fs = require('fs').promises;
const path = require('path');
dotenv.config();

const db = require('../db');

function parseFlags(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const val = argv[i + 1];
      if (val && !val.startsWith('--')) { out[key] = val; i++; }
      else out[key] = true;
    }
  }
  if (out.limit != null) {
    const n = Number(out.limit);
    out.limit = Number.isFinite(n) && n > 0 ? n : 20;
  }
  return out;
}

// ---------------- Helpers copied from Upwork pipeline for parity ----------------

function normalizeJobForFilter(node) {
  return node || {};
}

function getNum(v) { const x = Number(v); return Number.isFinite(x) ? x : null; }

function jobMatchesFilter(job, f) {
  try {
    if (!f) return true;
    const J = job?.job || job;
    const categoryId = job?.occupations?.category?.id || J?.occupations?.category?.id || job?.category || J?.category || null;
    if (Array.isArray(f.category_ids) && f.category_ids.length) {
      const ok = f.category_ids.map(String).includes(String(categoryId || ''));
      if (!ok) return false;
    }
    // Workload
    if (Array.isArray(f.workload) && f.workload.length) {
      const isFull = String(job?.engagement || J?.engagement || '').toLowerCase().includes('30+');
      const targetFull = f.workload.includes('full_time');
      const targetPart = f.workload.some(w => w === 'part_time' || w === 'as_needed');
      if (isFull && !targetFull) return false;
      if (!isFull && targetFull && !targetPart) return false;
    }
    // Verified payment
    if (typeof f.verified_payment_only === 'boolean' && f.verified_payment_only) {
      const verified = ((job?.client?.verificationStatus || J?.client?.verificationStatus || '')).toUpperCase() === 'VERIFIED';
      if (!verified) return false;
    }
    // Client hires
    const hires = getNum(job?.client?.totalHires ?? J?.client?.totalHires);
    if (f.client_hires_min != null && (hires == null || hires < Number(f.client_hires_min))) return false;
    if (f.client_hires_max != null && (hires == null || hires > Number(f.client_hires_max))) return false;
    // Hourly
    const hMin = getNum(job?.hourlyBudgetMin?.rawValue ?? J?.hourlyBudgetMin?.rawValue);
    const hMax = getNum(job?.hourlyBudgetMax?.rawValue ?? J?.hourlyBudgetMax?.rawValue);
    if (f.hourly_rate_min != null && (hMin == null || Number(f.hourly_rate_min) > (hMax ?? hMin))) return false;
    if (f.hourly_rate_max != null && (hMax == null || Number(f.hourly_rate_max) < (hMin ?? hMax))) return false;
    // Budget (fixed)
    const amount = getNum(job?.amount?.rawValue ?? J?.amount?.rawValue);
    if (f.budget_min != null && (amount == null || amount < Number(f.budget_min))) return false;
    if (f.budget_max != null && (amount == null || amount > Number(f.budget_max))) return false;
    // Proposals / applicants
    const applicants = getNum(job?.totalApplicants ?? J?.totalApplicants);
    if (f.proposal_min != null && (applicants == null || applicants < Number(f.proposal_min))) return false;
    if (f.proposal_max != null && (applicants == null || applicants > Number(f.proposal_max))) return false;
    // Experience
    if (f.experience_level && String(f.experience_level).length) {
      const exp = (job?.experienceLevel || J?.experienceLevel || '').toUpperCase();
      if (exp !== String(f.experience_level).toUpperCase()) return false;
    }
    return true;
  } catch {
    return false;
  }
}

async function main() {
  const flags = parseFlags(process.argv.slice(2));
  const focusCompanyId = flags.companyId ? String(flags.companyId) : null;
  const focusProfileId = flags.profileId ? String(flags.profileId) : null;
  const sampleLimit = (flags.limit != null) ? flags.limit : Number.POSITIVE_INFINITY;

  const jobsRes = await db.query('SELECT job_id, title, job_data FROM upwork_jobs ORDER BY inserted_at DESC');
  const allJobs = jobsRes.rows.map(r => ({ job_id: r.job_id, title: r.title, node: normalizeJobForFilter(r.job_data) }));

  const filtersRes = await db.query("SELECT platform, company_id, profile_id, active, category_ids, workload, verified_payment_only, client_hires_min, client_hires_max, hourly_rate_min, hourly_rate_max, budget_min, budget_max, proposal_min, proposal_max, experience_level FROM job_filters WHERE platform = 'upwork' AND active = TRUE");
  const profileRows = await db.query('SELECT id, name, company_id FROM profiles WHERE company_id IS NOT NULL');

  const profilesByCompany = new Map();
  for (const p of profileRows.rows) {
    if (focusCompanyId && String(p.company_id) !== focusCompanyId) continue;
    if (focusProfileId && String(p.id) !== focusProfileId) continue;
    const key = String(p.company_id);
    if (!profilesByCompany.has(key)) profilesByCompany.set(key, []);
    profilesByCompany.get(key).push({ id: String(p.id), name: p.name });
  }

  const filterByCompany = new Map();
  for (const f of filtersRes.rows) {
    const cid = String(f.company_id);
    if (!filterByCompany.has(cid)) filterByCompany.set(cid, { companyFilter: null, profileFilters: new Map() });
    const bucket = filterByCompany.get(cid);
    if (f.profile_id) {
      bucket.profileFilters.set(String(f.profile_id), f);
    } else {
      bucket.companyFilter = f;
    }
  }

  const report = {
    total_jobs: allJobs.length,
    companies: []
  };

  for (const [companyId, profileList] of profilesByCompany.entries()) {
    const filters = filterByCompany.get(companyId) || { companyFilter: null, profileFilters: new Map() };
    const companyEntry = {
      company_id: companyId,
      profiles: []
    };

    for (const prof of profileList) {
      const activeProfileFilter = filters.profileFilters.get(prof.id) || null;
      const f = activeProfileFilter || filters.companyFilter || null;
      const scope = activeProfileFilter ? 'profile' : (filters.companyFilter ? 'company' : 'none');

      const matched = [];
      for (const j of allJobs) {
        if (jobMatchesFilter(j.node, f)) matched.push(j);
      }

      companyEntry.profiles.push({
        profile_id: prof.id,
        filter_scope: scope,
        filter_used: f ? {
          category_ids: f.category_ids,
          workload: f.workload,
          verified_payment_only: f.verified_payment_only,
          client_hires_min: f.client_hires_min,
          client_hires_max: f.client_hires_max,
          hourly_rate_min: f.hourly_rate_min,
          hourly_rate_max: f.hourly_rate_max,
          budget_min: f.budget_min,
          budget_max: f.budget_max,
          proposal_min: f.proposal_min,
          proposal_max: f.proposal_max,
          experience_level: f.experience_level
        } : null,
        filtered_count: matched.length,
        job_ids: matched.slice(0, sampleLimit).map(m => m.job_id)
      });
    }

    report.companies.push(companyEntry);
  }

  const json = JSON.stringify(report, null, 2);
  const outPath = flags.out ? path.resolve(String(flags.out)) : path.join(__dirname, 'filterAudit-output.json');
  await fs.writeFile(outPath, json, 'utf8');
  console.log(`Wrote filter audit report to: ${outPath}`);
}

main().then(() => process.exit(0)).catch(err => { console.error('Audit failed:', err.message); process.exit(1); });


