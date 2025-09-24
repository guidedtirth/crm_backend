// upwork_fetch_available_fixed.js
// Only ACCESS_TOKEN is read from env.
//
// Run:
//   ACCESS_TOKEN=your_token node upwork_fetch_available_fixed.js

const fs = require('fs');
const path = require('path');
const axios = require('axios');

// ======= CONFIG (in-file) =======
const ENDPOINT = 'https://api.upwork.com/graphql';
const TENANT_ID = '';          // put your tenant id here if required, else leave ''
const PAGE_SIZE = 50;          // jobs per page
const MAX_PAGES = 3;           // how many pages to fetch
const SEARCH_EXPR = null;      // e.g. "react graphql" or null
const START_AFTER = "0";       // Upwork first-cursor
const SORT = [{ field: 'RECENCY' }];

// ======= ACCESS TOKEN from env only =======
const ACCESS_TOKEN = 'oauth2v2_f3a6a431a21741df92bd226772aa3f29' || '';
if (!ACCESS_TOKEN) {
  console.error('ACCESS_TOKEN missing. Provide via env: ACCESS_TOKEN=...');
  process.exit(1);
}

// ======= Request helper (your preferred shape) =======
const doRequest = async (token) => {
  const headers = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  if (TENANT_ID) headers['X-Upwork-API-TenantId'] = TENANT_ID;

  return axios.post(
    ENDPOINT,
    { query: global.queryBuilt, variables: global.variables },
    { headers, timeout: 20000 }
  );
};

// Only throw on *fatal* errors; log and continue on NullValueInNonNullableField
function handleGraphQLErrors(res) {
  const errs = res?.data?.errors;
  if (!Array.isArray(errs) || errs.length === 0) return;

  const soft = [];
  const fatal = [];
  for (const e of errs) {
    const cls = e?.extensions?.classification;
    if (cls === 'NullValueInNonNullableField') soft.push(e);
    else fatal.push(e);
  }

  if (soft.length) {
    const few = soft.slice(0, 3).map(e => ({
      message: e.message,
      path: e.path,
      classification: e?.extensions?.classification
    }));
    console.warn('⚠ GraphQL soft errors (null in non-nullable field) — continuing:\n', JSON.stringify(few, null, 2));
  }

  if (fatal.length) {
    throw new Error(`GraphQL fatal errors:\n${JSON.stringify(fatal, null, 2)}`);
  }
}

// ======= Query built ONLY from your AVAILABLE fields
// NOTE: removed client.companyOrgUid (causing your error)
const SEARCH_QUERY = `
  query JobsPage(
    $filter: MarketplaceJobPostingsSearchFilter
    $sort: [MarketplaceJobPostingSearchSortAttribute!]
  ) {
    marketplaceJobPostingsSearch(
      marketPlaceJobFilter: $filter
      searchType: USER_JOBS_SEARCH
      sortAttributes: $sort
    ) {
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
    }
  }
`;

// ======= Fetch all pages (pagination_eq) =======
async function fetchAllPages() {
  const nodes = [];
  let after = START_AFTER;

  for (let page = 0; page < MAX_PAGES; page++) {
    const filter = { pagination_eq: { first: PAGE_SIZE, after } };
    if (SEARCH_EXPR) filter.searchExpression_eq = SEARCH_EXPR;

    global.queryBuilt = SEARCH_QUERY;
    global.variables = { filter, sort: SORT };

    const res = await doRequest(ACCESS_TOKEN);
    handleGraphQLErrors(res); // soft errors logged; fatal ones throw

    const conn = res?.data?.data?.marketplaceJobPostingsSearch;
    const edges = Array.isArray(conn?.edges) ? conn.edges : [];
    nodes.push(...edges.map((e) => e.node));

    const pg = conn?.pageInfo || {};
    if (!pg?.hasNextPage || !pg?.endCursor) break;
    after = pg.endCursor;
  }

  return nodes;
}

// ======= Main =======
(async function main() {
  try {
    console.log('▶ Fetching Upwork jobs (AVAILABLE fields only)…');
    const nodes = await fetchAllPages();
    const out = path.resolve(__dirname, 'jobs_search_available.json');
    fs.writeFileSync(out, JSON.stringify(nodes, null, 2), 'utf8');
    console.log(`✓ Saved ${nodes.length} jobs → ${out}`);
  } catch (e) {
    console.error('✗ Error:', e?.response?.data || e?.message || e);
    process.exit(1);
  }
})();
