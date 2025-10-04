// Reseed upwork_jobs with the latest ~24 hours of jobs
// Usage: node tools/reseed_upwork_jobs_24h.js

const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');
const dotenv = require('dotenv');
const db = require('../db');
const { canonicalizeJobNode } = require('../platforms/upwork/utils');

async function loadUpworkEnv() {
  // Preferred: marketing_backend/.env (same as fetcher/tokenManager)
  const primary = path.resolve(__dirname, '../.env');
  const secondary = path.resolve(__dirname, '../platforms/.env');
  let parsed = {};
  // Try primary
  try {
    const content = await fs.readFile(primary, 'utf8');
    parsed = dotenv.parse(content);
  } catch (_) {
    // Fallback to secondary
    try {
      const content2 = await fs.readFile(secondary, 'utf8');
      parsed = dotenv.parse(content2);
    } catch (e2) {
      // Final fallback: environment variables already loaded in process.env
      parsed = {
        ACCESS_TOKEN: process.env.ACCESS_TOKEN,
        REFRESH_TOKEN: process.env.REFRESH_TOKEN,
        CLIENT_ID: process.env.CLIENT_ID,
        CLIENT_SECRET: process.env.CLIENT_SECRET,
        UPWORK_TENANT_ID: process.env.UPWORK_TENANT_ID,
      };
      if (!parsed.ACCESS_TOKEN || !parsed.REFRESH_TOKEN || !parsed.CLIENT_ID || !parsed.CLIENT_SECRET) {
        throw new Error(`Failed to read Upwork env at ${primary} or ${secondary}: ${e2.message}`);
      }
    }
  }
  const { ACCESS_TOKEN, REFRESH_TOKEN, CLIENT_ID, CLIENT_SECRET, UPWORK_TENANT_ID } = parsed;
  if (!ACCESS_TOKEN || !REFRESH_TOKEN || !CLIENT_ID || !CLIENT_SECRET) {
    throw new Error('Missing ACCESS_TOKEN / REFRESH_TOKEN / CLIENT_ID / CLIENT_SECRET in env');
  }
  return { accessToken: ACCESS_TOKEN, refreshToken: REFRESH_TOKEN, clientId: CLIENT_ID, clientSecret: CLIENT_SECRET, tenantId: UPWORK_TENANT_ID || '' };
}

function toGraphQLInputLiteral(value) {
  if (value === null) return 'null';
  if (value && typeof value === 'object' && '__enum' in value) return value.__enum;
  const t = typeof value;
  if (t === 'number' || t === 'boolean') return String(value);
  if (t === 'string') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(toGraphQLInputLiteral).join(', ') + ']';
  if (t === 'object') {
    return '{ ' + Object.entries(value).map(([k, v]) => `${k}: ${toGraphQLInputLiteral(v)}`).join(', ') + ' }';
  }
  return 'null';
}

async function fetchRecentJobs(accessToken, tenantId) {
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

  const headers = { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' };
  if (tenantId) headers['X-Upwork-API-TenantId'] = tenantId;

  const queryBuilt = (after) => {
    const filter = { pagination_eq: { first: 50, after: after || '0' } };
    const filterLiteral = toGraphQLInputLiteral(filter);
    return `
      query ($searchType: MarketplaceJobPostingSearchType, $sortAttributes: [MarketplaceJobPostingSearchSortAttribute]) {
        marketplaceJobPostingsSearch(
          marketPlaceJobFilter: ${filterLiteral}
          searchType: $searchType
          sortAttributes: $sortAttributes
        ) { ${SELECTION} }
      }
    `;
  };

  const variables = { searchType: 'USER_JOBS_SEARCH', sortAttributes: [{ field: 'RECENCY' }] };
  const sinceIso = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
  let newestIso = sinceIso;

  const nodes = [];
  let after = '0';
  let pages = 0;
  let keepGoing = true;
  while (keepGoing && pages < 30) {
    pages += 1;
    const resp = await axios.post('https://api.upwork.com/graphql', { query: queryBuilt(after), variables }, { headers, timeout: 15000 });
    const payload = resp.data?.data?.marketplaceJobPostingsSearch;
    const edges = payload?.edges || [];
    for (const e of edges) {
      const job = e.node;
      const created = job.createdDateTime || job.publishedDateTime || null;
      if (created && created <= sinceIso) { keepGoing = false; break; }
      if (created && created > newestIso) newestIso = created;
      nodes.push(job);
    }
    if (!keepGoing) break;
    const pi = payload?.pageInfo;
    if (!pi?.hasNextPage || !pi?.endCursor) break;
    after = pi.endCursor;
  }
  return nodes;
}

async function main() {
  console.log('Starting reseed: clearing upwork_jobs and fetching last 24h…');
  const { accessToken, tenantId } = await loadUpworkEnv();
  await db.query('TRUNCATE TABLE upwork_jobs RESTART IDENTITY');
  const jobs = await fetchRecentJobs(accessToken, tenantId);
  let inserted = 0;
  for (const raw of jobs) {
    try {
      const canon = canonicalizeJobNode(raw);
      const jobId = canon.id;
      const title = canon.title || 'Unknown Title';
      const budget = canon?.amount ? `${canon.amount.currency || ''} ${canon.amount.rawValue || ''}`.trim() : 'Unknown';
      const clientCountry = canon?.client?.location?.country || null;
      try {
        await db.query(
          `INSERT INTO upwork_jobs (job_id, title, job_data, inserted_at, client_country, budget)
           VALUES ($1,$2,$3,NOW(),$4,$5)
           ON CONFLICT (job_id) DO NOTHING`,
          [jobId, title, JSON.stringify(canon), clientCountry, budget]
        );
      } catch (colErr) {
        // Fallback if extended columns don't exist
        await db.query(
          `INSERT INTO upwork_jobs (job_id, title, job_data, inserted_at)
           VALUES ($1,$2,$3,NOW())
           ON CONFLICT (job_id) DO NOTHING`,
          [jobId, title, JSON.stringify(canon)]
        );
      }
      inserted += 1;
    } catch (e) {
      console.warn('Insert failed:', e.message);
    }
  }
  console.log(`Done. Inserted ${inserted} job(s) from last 24 hours.`);
  process.exit(0);
}

main().catch((e) => { console.error('Reseed failed:', e.message); process.exit(1); });


