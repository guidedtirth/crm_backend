/**
 * Upwork platform fetcher
 * Incremental job sync, internal filtering, assistant scoring, and proposal persistence.
 */
const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const dotenv = require('dotenv');
const cron = require('node-cron');
const { getAssistantId, initializeAssistant } = require('../../assistant');
const db = require('../../db');
const OpenAI = require('openai');

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

// Structured, minimal logging for pipeline
function pipelineLog(event, data) {
  try { console.log(JSON.stringify({ ts: new Date().toISOString(), event, ...data })); } catch {}
}

// Load environment variables
dotenv.config();



// Helper to refresh and persist Upwork access token (fallback in case scheduled refresh hasn't run yet)
async function refreshAccessToken(refreshToken, clientId, clientSecret) {
  try {
    const response = await axios.post(
      'https://www.upwork.com/api/v3/oauth2/token',
      new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
        client_id: clientId,
        client_secret: clientSecret,
      }).toString(),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );
    const { access_token, refresh_token } = response.data; // Gets new tokens
    const envPath = path.resolve(__dirname, '../../.env');
    let envContent = await fs.readFile(envPath, 'utf8');
    envContent = envContent.replace(/ACCESS_TOKEN=.*/, `ACCESS_TOKEN=${access_token}`);
    if (refresh_token) {
      envContent = envContent.replace(/REFRESH_TOKEN=.*/, `REFRESH_TOKEN=${refresh_token}`);
    }
    await fs.writeFile(envPath, envContent);
    return access_token;  // Returns new access token
  } catch (error) {
    console.error('Refresh token failed:', error.response?.data?.error || error.message);
    throw new Error('Failed to refresh token. Re-authenticate manually at https://www.upwork.com/developer/apps');
  }
}

let isPipelineRunning = false;
let assistantReady = false;

async function ensureAssistantReady() {
  if (assistantReady) return true;

  try {
    let assistantId = getAssistantId();

    if (!assistantId) {
      assistantId = await initializeAssistant();
    }

    if (!assistantId) {
      throw new Error('Assistant initialization failed');
    }
    assistantReady = true;
    return true;
  } catch (err) {
    console.error('Assistant preparation failed:', err);
    throw err;
  }
}

// --------------------------- Enum literal helper ---------------------------
// Wrap enum values so the serializer outputs them UNQUOTED.
const enumVal = (name) => ({ __enum: String(name) });

// ------------------------ GraphQL literal serializer -----------------------
function toGraphQLInputLiteral(value) {
  if (value === null) return "null";
  if (value && typeof value === "object" && "__enum" in value) {
    return value.__enum;
  }
  const t = typeof value;
  if (t === "number" || t === "boolean") return String(value);
  if (t === "string") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(toGraphQLInputLiteral).join(", ") + "]";
  if (t === "object") {
    return (
      "{ " +
      Object.entries(value)
        .map(([k, v]) => `${k}: ${toGraphQLInputLiteral(v)}`)
        .join(", ") +
      " }"
    );
  }
  return "null";
}

// -------------------------- Introspection: IntRange ------------------------
async function introspectIntRange(token, tenantId) {
  const q = `
    query {
      __type(name: "IntRange") {
        inputFields { name }
      }
    }
  `;
  const headers = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
  if (tenantId) headers["X-Upwork-API-TenantId"] = tenantId;
  const resp = await axios.post(
    "https://api.upwork.com/graphql",
    { query: q },
    { headers, timeout: 20000 }
  );
  const errs = resp.data?.errors;
  if (errs?.length) throw new Error(JSON.stringify(errs));
  const names = (resp.data?.data?.__type?.inputFields || []).map((f) => f.name);
  const pairs = [
    ["min", "max"],
    ["from", "to"],
    ["low", "high"],
    ["start", "end"],
  ];
  for (const [a, b] of pairs) if (names.includes(a) && names.includes(b)) return { lowKey: a, highKey: b };
  if (names.length >= 2) return { lowKey: names[0], highKey: names[1] };
  throw new Error("Could not determine IntRange field names");
}

// ------------------------------ Load DB Filters ----------------------------
async function loadUpworkFiltersFromDb() {
  try {
    const r = await db.query("SELECT * FROM job_filters WHERE platform = 'upwork' ORDER BY id ASC LIMIT 1");
    if (r.rows.length === 0) {
      return {
        category_ids: [],
        job_type: 'HOURLY',
        workload: [],
        verified_payment_only: true,
        client_hires_min: 1,
        client_hires_max: 100000,
        hourly_rate_min: 15,
        hourly_rate_max: 1000,
        budget_min: 5000,
        budget_max: 10000000,
        proposal_min: 0,
        proposal_max: 50,
        experience_level: null,
      };
    }
    const row = r.rows[0];
    return {
      category_ids: Array.isArray(row.category_ids) ? row.category_ids : [],
      job_type: row.job_type || 'HOURLY',
      workload: Array.isArray(row.workload)
        ? row.workload.map((v) => String(v).toLowerCase())
        : (row.workload ? [String(row.workload).toLowerCase()] : []),
      verified_payment_only: Boolean(row.verified_payment_only),
      client_hires_min: Number(row.client_hires_min ?? 1),
      client_hires_max: Number(row.client_hires_max ?? 100000),
      hourly_rate_min: Number(row.hourly_rate_min ?? 15),
      hourly_rate_max: Number(row.hourly_rate_max ?? 1000),
      budget_min: Number(row.budget_min ?? 5000),
      budget_max: Number(row.budget_max ?? 10000000),
      proposal_min: Number(row.proposal_min ?? 0),
      proposal_max: Number(row.proposal_max ?? 50),
      experience_level: row.experience_level || null,
    };
  } catch (e) {
    console.warn('Failed to load upwork filters from DB, using defaults:', e.message);
    return {
      category_ids: [],
      job_type: 'HOURLY',
      workload: 'FULL_TIME',
      verified_payment_only: true,
      client_hires_min: 1,
      client_hires_max: 100000,
      hourly_rate_min: 15,
      hourly_rate_max: 1000,
      budget_min: 5000,
      budget_max: 10000000,
      proposal_min: 0,
      proposal_max: 50,
      experience_level: null,
    };
  }
}

// -------------------- Incremental sync state (time-window only) --------------------
const STATE_PATH = path.resolve(__dirname, 'upwork_sync_state.json');
async function readSyncState() {
  try { return JSON.parse(await fs.readFile(STATE_PATH, 'utf8')); } catch { return {}; }
}
async function writeSyncState(state) {
  try { await fs.writeFile(STATE_PATH, JSON.stringify(state, null, 2), 'utf8'); } catch {}
}

async function fetchLatestJobs() {
  const now = new Date();

  try {
    const envPath = path.resolve(__dirname, '../../.env');
    const envConfig = dotenv.parse(await fs.readFile(envPath));
    let accessToken = envConfig.ACCESS_TOKEN;
    const refreshToken = envConfig.REFRESH_TOKEN;
    const clientId = envConfig.CLIENT_ID;
    const clientSecret = envConfig.CLIENT_SECRET;
    const tenantId = envConfig.UPWORK_TENANT_ID || '';

    if (!accessToken || !refreshToken || !clientId || !clientSecret) {
      throw new Error('Missing ACCESS_TOKEN, REFRESH_TOKEN, CLIENT_ID, or CLIENT_SECRET in .env');
    }

    // Time window state: first run → last 24h; subsequent runs → since lastFetchedAt
    const sync = await readSyncState();
    const sinceIso = sync.lastFetchedAt || new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    let newestIso = sinceIso;

    const SELECTION = `
      totalCount
      edges {
        node {
          id
          title
          description
          ciphertext
          duration
          durationLabel
          engagement
          amount { rawValue currency }
          recordNumber
          experienceLevel
          category
          subcategory
          freelancersToHire
          relevance {
            id
            effectiveCandidates
            recommendedEffectiveCandidates
            uniqueImpressions
            publishTime
            hoursInactive
          }
          enterprise
          relevanceEncoded
          totalApplicants
          preferredFreelancerLocation
          preferredFreelancerLocationMandatory
          premium
          clientNotSureFields
          clientPrivateFields
          applied
          createdDateTime
          publishedDateTime
          renewedDateTime
          client {
            totalHires
            totalPostedJobs
            totalSpent { rawValue currency }
            verificationStatus
            location { country city }
            totalReviews
            totalFeedback
            companyRid
            edcUserId
            lastContractPlatform
            lastContractRid
            lastContractTitle
            hasFinancialPrivacy
          }
          skills { name }
          occupations {
            category { id prefLabel }
            subCategories { id prefLabel }
            occupationService { id prefLabel }
          }
          hourlyBudgetType
          hourlyBudgetMin { rawValue currency }
          hourlyBudgetMax { rawValue currency }
          localJobUserDistance
          weeklyBudget { rawValue currency }
          engagementDuration { weeks }
          totalFreelancersToHire
          teamId
          freelancerClientRelation { __typename }

          job {
            id
            content { title description }
            attachments { id }
            contractTerms {
              hourlyContractTerms { engagementDuration { weeks } }
              fixedPriceContractTerms { engagementDuration { weeks } }
            }
          }
        }
      }
      pageInfo { hasNextPage endCursor }
    `;
    const fetchPage = async (after) => {
      const filter = { pagination_eq: { first: 50, after: after || '0' } };
      const filterLiteral = toGraphQLInputLiteral(filter);
    const queryBuilt = `
      query ($searchType: MarketplaceJobPostingSearchType, $sortAttributes: [MarketplaceJobPostingSearchSortAttribute]) {
        marketplaceJobPostingsSearch(
          marketPlaceJobFilter: ${filterLiteral}
          searchType: $searchType
          sortAttributes: $sortAttributes
        ) { ${SELECTION} }
      }
    `;
    const variables = {
      searchType: 'USER_JOBS_SEARCH',
      sortAttributes: [{ field: 'RECENCY' }],
    };
      const headers = {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      };
      if (tenantId) headers['X-Upwork-API-TenantId'] = tenantId;
      try {
        return await axios.post('https://api.upwork.com/graphql', { query: queryBuilt, variables }, { headers, timeout: 10000 });
    } catch (err) {
      if (err.response?.status === 401) {
        console.error('⚠️ Access token invalid. Attempting to refresh via tokenManager...');
        const tm = require('./tokenManager');
        const newAccess = await tm();
        if (!newAccess) throw err;
        accessToken = newAccess;
          const headers2 = { ...headers, Authorization: `Bearer ${accessToken}` };
          return await axios.post('https://api.upwork.com/graphql', { query: queryBuilt, variables }, { headers: headers2, timeout: 10000 });
        }
        throw err;
      }
    };

    const collected = [];
    let after = '0';
    let keepGoing = true;
    let pages = 0;
    while (keepGoing && pages < 20) {
      pages += 1;
      const resp = await fetchPage(after);
      const payload = resp.data?.data?.marketplaceJobPostingsSearch;
      const edges = payload?.edges || [];
      const nodes = edges.map(e => e.node);
      for (const job of nodes) {
        const created = job.createdDateTime || job.publishedDateTime || null;
        if (created) {
          if (created > newestIso) newestIso = created;
          if (created <= sinceIso) { keepGoing = false; break; }
        }
        collected.push(job);
      }
      if (!keepGoing) break;
      const pi = payload?.pageInfo;
      if (!pi?.hasNextPage || !pi?.endCursor) break;
      after = pi.endCursor;
    }
    // silent

    for (const job of collected) {
      try {
        const budget = job.amount ? `${job.amount.currency} ${job.amount.rawValue}` : 'Unknown';

        // Use the raw node exactly as returned by Upwork (no normalization)
        const rawNode = job;
        const jobDataToStore = rawNode; // store raw
        const jobIdToStore = rawNode?.id || rawNode?.job?.id || null;
        const titleToStore = rawNode?.title || rawNode?.job?.content?.title || 'Unknown Title';

        // DB insert with normalized job_data; fallback if extended columns missing
        let insertResult;
        try {
          insertResult = await db.query(
            `INSERT INTO upwork_jobs (job_id, title, job_data, inserted_at, proposal_generated, client_country, budget)
             VALUES ($1, $2, $3, NOW(), FALSE, $4, $5)
             ON CONFLICT (job_id) DO NOTHING
             RETURNING id`,
            [ jobIdToStore, titleToStore, JSON.stringify(jobDataToStore), rawNode?.client?.location?.country || null, budget ]
          );
        } catch (colErr) {
          console.warn('Extended columns missing; using basic insert:', colErr.message);
          insertResult = await db.query(
            `INSERT INTO upwork_jobs (job_id, title, job_data, inserted_at, proposal_generated)
             VALUES ($1, $2, $3, NOW(), FALSE)
             ON CONFLICT (job_id) DO NOTHING
             RETURNING id`,
            [jobIdToStore, titleToStore, JSON.stringify(jobDataToStore)]
          );
        }
        // silent per-job store
      } catch (dbError) {
        console.error('Database insertion error:', dbError.message);
      }
    }

    await writeSyncState({ lastFetchedAt: newestIso });
    return collected;
  } catch (error) {
    console.error('Error in job processing:', error.message);
    throw error;
  }
}

// Compatibility helper retained (no longer used by pipeline)
async function generateProposal(job, job_id) {
  try {
    await ensureAssistantReady();
    const assistantId = getAssistantId();
    if (!assistantId) throw new Error('Assistant ID not available');

    const skills = Array.isArray(job?.skills)
      ? job.skills.map(s => s.name || s.prettyName || '').filter(Boolean)
      : [];
    // Support both shapes: full node and nested raw.job
    const title = job?.title || job?.content?.title || job?.job?.content?.title || 'Unknown Title';
    const job_id_final = job_id || job?.id || job?.job_id || job?.job?.id || null; // Upwork job_id (text)
    const description = job?.description || job?.content?.description || job?.job?.content?.description || '';
    const queryText = `${title} ${description} ${skills.join(' ')}`;

    // Find best profile by embeddings
    const emb = await openai.embeddings.create({ input: queryText, model: 'text-embedding-3-small' });
    const queryEmbedding = emb.data[0].embedding;

    const embRes = await db.query('SELECT profile_id, chunk, embedding FROM embeddings');
    let highestScore = -1;
    let bestProfileId = null;
    const relevantChunks = [];

    function cos(a, b) {
      let d = 0, na = 0, nb = 0;
      for (let i = 0; i < a.length && i < b.length; i++) { d += a[i] * b[i]; na += a[i]*a[i]; nb += b[i]*b[i]; }
      return (na && nb) ? d / (Math.sqrt(na) * Math.sqrt(nb)) : 0;
    }

    for (const row of embRes.rows) {
      const e = Array.isArray(row.embedding) ? row.embedding : JSON.parse(row.embedding);
      const score = cos(queryEmbedding, e);
      if (score > highestScore) { highestScore = score; bestProfileId = row.profile_id; }
      if (score > 0.7) relevantChunks.push(row.chunk);
    }

    // Enforce minimum relevance: skip proposal generation if score < 80%
    if (!bestProfileId || highestScore < 0.8) {
      return { relevance: 'No', score: Math.floor(Math.max(0, highestScore) * 100), proposal: 'No sufficiently relevant profile (>=80) to generate a proposal.', thread_id: null };
    }

    const prof = await db.query('SELECT name, content FROM profiles WHERE id = $1', [bestProfileId]);
    const profileName = prof.rows[0]?.name || 'Unknown';
    const profileContent = (prof.rows[0]?.content || '') + (relevantChunks.length ? ('\n\n' + relevantChunks.join('\n')) : '');

    // Create thread and run assistant (using SDK - works fine)
    const thread = await openai.beta.threads.create();

    await openai.beta.threads.messages.create(
      thread.id,
      {
        role: 'user',
        content: `Profile: ${profileContent}\nJob: ${queryText}\nBudget Range: $150-1000\nGenerate a job proposal in plain text format, tailored to the candidate's profile. Do not use any markdown symbols.`
      }
    );

    let run = await openai.beta.threads.runs.create(
      thread.id,
      { assistant_id: assistantId }
    );

    // Polling loop with raw Axios for retrieve (bypasses SDK bug, adds required beta header)
    let pollCount = 0;
    while (run.status !== 'completed') {
      pollCount++;
      await new Promise(r => setTimeout(r, 800));

      // Raw HTTP call to official API endpoint: GET /v1/threads/{thread_id}/runs/{run_id}
      const apiUrl = `https://api.openai.com/v1/threads/${thread.id}/runs/${run.id}`;
      const response = await axios.get(apiUrl, {
        headers: {
          Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
          'Content-Type': 'application/json',
          'OpenAI-Beta': 'assistants=v2',  // FIXED: Required header for Assistants API v2
        },
        timeout: 10000,  // 10s timeout for safety
      });
      run = response.data;  // Update run object with API response (matches SDK structure)

      if (['failed', 'cancelled', 'expired'].includes(run.status)) {
        throw new Error(`Assistant run ${run.status}: ${run.last_error?.message || 'Unknown error'}`);
      }
      if (pollCount > 30) throw new Error('Polling timeout - run not completing');
    }

    const messages = await openai.beta.threads.messages.list(
      thread.id,
      {
        limit: 1,
        order: 'desc'
      }
    );
    const proposal = messages.data[0]?.content?.[0]?.text?.value || '';

    // Store feedback row
    const feedbackId = uuidv4();
    // Deduplicate by job_id (store external Upwork job_id)
    if (job_id_final) {
      try {
        const exists = await db.query('SELECT 1 FROM proposal_feedback WHERE job_id = $1 LIMIT 1', [job_id_final]);
        if (exists.rowCount > 0) {
          await db.query('UPDATE upwork_jobs SET proposal_generated = TRUE WHERE job_id = $1', [job_id_final]);
        } else {
          await db.query(
            'INSERT INTO proposal_feedback (id, profile_id, job_id, query_text, feedback, proposal, thread_id, score, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())',
            [feedbackId, bestProfileId, job_id_final, JSON.stringify({ id: job_id_final, title }), null, proposal, thread.id, Math.floor(highestScore * 100)]
          );
        }
      } catch (dupErr) {
        console.warn('proposal_feedback dedup check failed:', dupErr.message);
        await db.query(
          'INSERT INTO proposal_feedback (id, profile_id, job_id, query_text, feedback, proposal, thread_id, score, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())',
          [feedbackId, bestProfileId, job_id_final, JSON.stringify({ id: job_id_final, title }), null, proposal, thread.id, Math.floor(highestScore * 100)]
        );
      }
    } else {
      await db.query(
        'INSERT INTO proposal_feedback (id, profile_id, job_id, query_text, feedback, proposal, thread_id, score, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())',
        [feedbackId, bestProfileId, null, JSON.stringify({ id: null, title }), null, proposal, thread.id, Math.floor(highestScore * 100)]
      );
    }

    return { relevance: 'Yes', score: Math.floor(highestScore * 100), proposal, profile_id: bestProfileId, profile_name: profileName, thread_id: thread.id };
  } catch (err) {
    console.error('❌ Proposal generation failed:', err.message);
    if (err.response && err.response.status === 400) {
      console.error('DEBUG: Full 400 response body:', err.response.data);  // e.g., { error: { message: 'Invalid run ID' } }
    }
    console.error('Full error:', err);
    throw err;
  }
}
// ---------------- New filtering and per-profile processing (no embeddings) ----------------

function normalizeJobForFilter(node) {
  // Keep original node; many fields are at top-level, while nested job holds content/contractTerms
  return node || {};
}

function getNum(v) { const x = Number(v); return Number.isFinite(x) ? x : null; }

function jobMatchesFilter(job, f) {
  try {
    if (!f) return true;
    const J = job?.job || job; // nested job fallback
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

async function loadActiveFiltersByCompany(companyId) {
  const rows = await db.query(
    `SELECT profile_id, active, category_ids, workload, verified_payment_only,
            client_hires_min, client_hires_max,
            hourly_rate_min, hourly_rate_max,
            budget_min, budget_max,
            proposal_min, proposal_max,
            experience_level
       FROM job_filters
      WHERE platform = 'upwork' AND company_id = $1 AND active = TRUE`,
    [companyId]
  );
  const profileFilters = new Map();
  let companyFilter = null;
  for (const r of rows.rows) {
    if (r.profile_id) profileFilters.set(String(r.profile_id), r);
    else companyFilter = r;
  }
  return { companyFilter, profileFilters };
}

async function ensureChatTables() {
  // Create chat thread/message tables if missing (mirrors chatController)
  await db.query(`
    CREATE TABLE IF NOT EXISTS profile_chat_threads (
      id UUID PRIMARY KEY,
      profile_id UUID NOT NULL,
      thread_id TEXT NOT NULL,
      title TEXT,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
  `);
  await db.query(`CREATE INDEX IF NOT EXISTS idx_profile_chat_threads_profile ON profile_chat_threads(profile_id);`);
  await db.query(`CREATE UNIQUE INDEX IF NOT EXISTS uq_profile_chat_thread_latest ON profile_chat_threads(profile_id, thread_id);`);
  await db.query(`
    CREATE TABLE IF NOT EXISTS profile_chat_messages (
      id UUID PRIMARY KEY,
      profile_id UUID NOT NULL,
      thread_id TEXT NOT NULL,
      role TEXT NOT NULL CHECK (role IN ('user','assistant')),
      content TEXT,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
  `);
  await db.query(`CREATE INDEX IF NOT EXISTS idx_profile_chat_messages_thread ON profile_chat_messages(thread_id, created_at);`);
  try { await db.query("ALTER TABLE profile_chat_messages ADD COLUMN IF NOT EXISTS content_enc TEXT"); } catch (e) {}
  try { await db.query("ALTER TABLE profile_chat_messages ADD COLUMN IF NOT EXISTS content_nonce TEXT"); } catch (e) {}
  try { await db.query("ALTER TABLE profile_chat_messages ADD COLUMN IF NOT EXISTS content_salt TEXT"); } catch (e) {}
  try { await db.query("ALTER TABLE profile_chat_messages ALTER COLUMN content DROP NOT NULL"); } catch (e) {}
}

async function ensureProposalFeedbackTable() {
  await db.query(`
    CREATE TABLE IF NOT EXISTS proposal_feedback (
      id UUID PRIMARY KEY,
      profile_id UUID NOT NULL,
      job_id TEXT,
      query_text TEXT,
      feedback TEXT,
      proposal TEXT,
      thread_id TEXT,
      score INTEGER,
      created_at TIMESTAMPTZ DEFAULT NOW()
    );
  `);
  await db.query(`CREATE INDEX IF NOT EXISTS idx_proposal_feedback_profile ON proposal_feedback(profile_id);`);
  await db.query(`CREATE INDEX IF NOT EXISTS idx_proposal_feedback_job_profile ON proposal_feedback(job_id, profile_id);`);
}

async function ensureProfileThread(profileId) {
  // Reuse latest thread if exists else create
  const existing = await db.query('SELECT thread_id FROM profile_chat_threads WHERE profile_id = $1 ORDER BY created_at DESC LIMIT 1', [profileId]);
  if (existing.rows.length > 0) return existing.rows[0].thread_id;
  const thread = await openai.beta.threads.create();
  const id = uuidv4();
  await db.query('INSERT INTO profile_chat_threads (id, profile_id, thread_id, title) VALUES ($1, $2, $3, $4)', [id, profileId, thread.id, 'Auto']);
  return thread.id;
}

function extractJson(text) {
  if (!text) return null;
  const m = text.match(/\{[\s\S]*\}/);
  if (!m) return null;
  try { return JSON.parse(m[0]); } catch { return null; }
}

async function pollRunLocal(threadId, runId) {
  let run = { id: runId, status: 'queued' };
  let attempts = 0;
  while (run.status !== 'completed') {
    attempts += 1;
    await new Promise(r => setTimeout(r, 800));
    const apiUrl = `https://api.openai.com/v1/threads/${threadId}/runs/${runId}`;
    const resp = await axios.get(apiUrl, {
      headers: {
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        'Content-Type': 'application/json',
        'OpenAI-Beta': 'assistants=v2'
      },
      timeout: 15000
    });
    run = resp.data;
    if (['failed','cancelled','expired'].includes(run.status)) {
      throw new Error(`Assistant run ${run.status}: ${run.last_error?.message || 'unknown'}`);
    }
    if (attempts > 40) throw new Error('Polling timeout');
  }
}

async function assessAndMaybeGenerate(job, companyId, profileId) {
  const title = job?.title || job?.content?.title || job?.job?.content?.title || 'Unknown Title';
  const description = job?.description || job?.content?.description || job?.job?.content?.description || '';
  const skills = Array.isArray(job?.skills) ? job.skills.map(s => s.name || s.prettyName || '').filter(Boolean) : [];
  // Reuse the user's existing chat thread so the assistant knows the user context
  const threadId = await ensureProfileThread(profileId);

  // Serialize full job payload (prefer nested raw.job if present)
  const jobPayload = job?.job ? job.job : job;
  let jobJson = '';
  try { jobJson = JSON.stringify(jobPayload); } catch { jobJson = JSON.stringify({ title, description, skills }); }
  // Guardrail: cap extremely large payloads
  if (jobJson.length > 60000) jobJson = jobJson.slice(0, 60000) + '\n/* truncated */';

  const prompt = [
    `You are an assistant evaluating job-to-user fit and writing proposals.`,
    `Use ONLY the job title and the JSON job object provided below (plus any prior thread context).`,
    `Return STRICT JSON with keys: score (0-100), suitable (true/false), proposal (string).`,
    `If suitable >= 80, include a concise, tailored plain-text proposal (no markdown).`,
    `JOB_TITLE: ${title}`,
    `JOB_JSON_START`,
    jobJson,
    `JOB_JSON_END`
  ].join('\n');

  await openai.beta.threads.messages.create(threadId, { role: 'user', content: prompt });
  const assistantId = getAssistantId();
  const run = await openai.beta.threads.runs.create(threadId, { assistant_id: assistantId });
  await pollRunLocal(threadId, run.id);
  const messages = await openai.beta.threads.messages.list(threadId, { limit: 1, order: 'desc' });
  const text = messages.data[0]?.content?.[0]?.text?.value || '';
  const parsed = extractJson(text) || {};
  const score = Number(parsed.score || parsed.compatibility || 0);
  const suitable = (parsed.suitable === true) && (score >= 80);
  const proposal = String(parsed.proposal || '').trim();
  return { suitable, score: Math.floor(score), proposal, threadId };
}

async function processNewJobs(jobs) {
  try {
    await ensureChatTables();
    await ensureProposalFeedbackTable();
    // Collect companies with profiles
    const companies = await db.query('SELECT DISTINCT company_id FROM profiles WHERE company_id IS NOT NULL');
    let generated = 0;
    for (const c of companies.rows) {
      const companyId = c.company_id;
      const { companyFilter, profileFilters } = await loadActiveFiltersByCompany(companyId);
      const profRows = await db.query('SELECT id, name FROM profiles WHERE company_id = $1', [companyId]);
      for (const pr of profRows.rows) {
        const profileId = String(pr.id);
        const hasProfile = profileFilters.has(profileId);
        const filter = profileFilters.get(profileId) || companyFilter || null; // pass-all if none configured
        const filterScope = hasProfile ? 'profile' : (companyFilter ? 'company' : 'none');

        const filteredJobIds = [];
        for (const node of jobs) {
          const externalJobId = node?.id || node?.job?.id || null;
          if (!externalJobId) continue;

          // Skip if already generated for this profile+job
          const exists = await db.query('SELECT 1 FROM proposal_feedback WHERE job_id = $1 AND profile_id = $2 LIMIT 1', [externalJobId, profileId]);
          if (exists.rowCount > 0) continue;

          // Load canonical job_data from DB (exact JSONB we persisted)
          let jobNode = null;
          try {
            const jd = await db.query('SELECT job_data FROM upwork_jobs WHERE job_id = $1 LIMIT 1', [externalJobId]);
            jobNode = jd.rows[0]?.job_data || null;
          } catch {}
          if (!jobNode) jobNode = normalizeJobForFilter(node);

          if (!jobMatchesFilter(jobNode, filter)) continue;
          filteredJobIds.push(externalJobId);

          try {
            const { suitable, score, proposal, threadId } = await assessAndMaybeGenerate(jobNode, companyId, profileId);
            if (!suitable || score < 80 || !proposal) continue;

            const feedbackId = uuidv4();
            // Create a fresh thread for the saved proposal (refinement thread)
            let saveThreadId = null;
            try {
              const t = await openai.beta.threads.create();
              saveThreadId = t.id;
              // Seed the new thread with the generated proposal text for future refinements
              await openai.beta.threads.messages.create(saveThreadId, { role: 'assistant', content: proposal });
            } catch (_) { saveThreadId = threadId; }
            await db.query(
              'INSERT INTO proposal_feedback (id, profile_id, job_id, query_text, feedback, proposal, thread_id, score, created_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,NOW())',
              [feedbackId, profileId, externalJobId, JSON.stringify({ id: externalJobId, title: (jobNode.title || jobNode?.content?.title || '') }), null, proposal, saveThreadId, score]
            );
            // Optional: flag job as having at least one proposal
            try { await db.query('UPDATE upwork_jobs SET proposal_generated = TRUE WHERE job_id = $1', [externalJobId]); } catch {}
            generated++;
            pipelineLog('score', { companyId, profileId, jobId: externalJobId, score, suitable: true, saved: true });
          } catch (e) {
            console.warn(`profile ${profileId} job ${externalJobId} generation failed: ${e.message}`);
          }
        }
        pipelineLog('filter.used', { companyId, profileId, scope: filterScope, filteredCount: filteredJobIds.length, jobIds: filteredJobIds });
      }
    }
    return generated;
  } catch (err) {
    console.error('Job processing failed:', err.message);
    throw err;
  }
}

async function runJobPipeline() {
  if (isPipelineRunning) {
    console.log('⚠️ Pipeline already running, skipping');
    return;
  }

  isPipelineRunning = true;
  try {
    await ensureAssistantReady();
    const jobs = await fetchLatestJobs();
    const processedCount = await processNewJobs(jobs);
    pipelineLog('pipeline.done', { fetched: jobs.length, processed: processedCount });
  } catch (err) {
    console.error('Pipeline failed:', err.message);
  } finally {
    isPipelineRunning = false;
  }
}

async function startApplication() {
  try {

    // Initialize assistant
    await ensureAssistantReady();

    // Initial run
    await runJobPipeline();

    // Schedule regular runs
    cron.schedule('*/5 * * * *', () => { runJobPipeline().catch(console.error); });
  } catch (startupError) {
    console.error('Startup failed:', startupError.message);
    process.exit(1);
  }
}

// Start the application
startApplication();

// Keep process alive
process.stdin.resume();

// Graceful shutdown
process.on('SIGINT', async () => {
  try {
    await db.end();
    // silent
    process.exit(0);
  } catch (err) {
    console.error('Shutdown error:', err);
    process.exit(1);
  }
});

// Handle uncaught errors
process.on('unhandledRejection', (err) => {
  console.error('⚠️ Unhandled rejection:', err);
});

process.on('uncaughtException', (err) => {
  console.error('⚠️ Uncaught exception:', err);
});