const db = require('./db');

async function ensureTenantSchema() {
  // Companies table
  await db.query(`
    CREATE TABLE IF NOT EXISTS companies (
      id UUID PRIMARY KEY,
      name TEXT NOT NULL,
      created_at TIMESTAMPTZ DEFAULT NOW()
    );
  `);
  // Companies auth fields
  try { await db.query('ALTER TABLE companies ADD COLUMN IF NOT EXISTS email TEXT'); } catch (_) {}
  try { await db.query('ALTER TABLE companies ADD COLUMN IF NOT EXISTS password TEXT'); } catch (_) {}
  try { await db.query('CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_name_email ON companies(name, email)'); } catch (_) {}

  // Profiles.company_id
  try { await db.query('ALTER TABLE profiles ADD COLUMN IF NOT EXISTS company_id UUID'); } catch (_) {}
  try { await db.query('CREATE INDEX IF NOT EXISTS idx_profiles_company ON profiles(company_id)'); } catch (_) {}
  // Profiles auth fields
  try { await db.query('ALTER TABLE profiles ADD COLUMN IF NOT EXISTS email TEXT'); } catch (_) {}
  try { await db.query('ALTER TABLE profiles ADD COLUMN IF NOT EXISTS password TEXT'); } catch (_) {}
  try { await db.query('CREATE UNIQUE INDEX IF NOT EXISTS uq_profiles_email_company ON profiles(email, company_id)'); } catch (_) {}

  // Ensure upwork_jobs table and constraints for ON CONFLICT(job_id)
  await db.query(`
    CREATE TABLE IF NOT EXISTS upwork_jobs (
      id SERIAL PRIMARY KEY,
      job_id TEXT UNIQUE,
      title TEXT,
      job_data JSONB,
      inserted_at TIMESTAMPTZ DEFAULT NOW(),
      proposal_generated BOOLEAN DEFAULT FALSE
    );
  `);
  try { await db.query('CREATE UNIQUE INDEX IF NOT EXISTS uq_upwork_jobs_job_id ON upwork_jobs(job_id)'); } catch (_) {}
  try { await db.query('ALTER TABLE upwork_jobs ADD COLUMN IF NOT EXISTS client_country TEXT'); } catch (_) {}
  try { await db.query('ALTER TABLE upwork_jobs ADD COLUMN IF NOT EXISTS budget TEXT'); } catch (_) {}

  // job_filters.company_id and indexes
  try { await db.query('ALTER TABLE job_filters ADD COLUMN IF NOT EXISTS company_id UUID'); } catch (_) {}
  // Remove legacy global unique that blocks per-user filters
  try { await db.query('DROP INDEX IF EXISTS uq_job_filters_platform_company'); } catch (_) {}

  // job_filters: support company default vs user-specific and active flag
  try { await db.query('ALTER TABLE job_filters ADD COLUMN IF NOT EXISTS profile_id UUID'); } catch (_) {}
  try { await db.query('ALTER TABLE job_filters ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT FALSE'); } catch (_) {}
  // One default per company (profile_id IS NULL)
  try { await db.query("CREATE UNIQUE INDEX IF NOT EXISTS uq_job_filters_company_default ON job_filters(platform, company_id) WHERE profile_id IS NULL"); } catch (_) {}
  // One filter per profile
  try { await db.query('CREATE UNIQUE INDEX IF NOT EXISTS uq_job_filters_profile ON job_filters(platform, company_id, profile_id)'); } catch (_) {}
  // Helpful index
  try { await db.query('CREATE INDEX IF NOT EXISTS idx_job_filters_company_profile_active ON job_filters(company_id, profile_id, active)'); } catch (_) {}
}

module.exports = { ensureTenantSchema };


