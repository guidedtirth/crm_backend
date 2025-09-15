const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const dotenv = require('dotenv');
const cron = require('node-cron');
const { getAssistantId, initializeAssistant } = require('./assistant');
const db = require('./db');
const OpenAI = require('openai');

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

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
    const envPath = path.resolve(__dirname, '.env');
    let envContent = await fs.readFile(envPath, 'utf8');
    envContent = envContent.replace(/ACCESS_TOKEN=.*/, `ACCESS_TOKEN=${access_token}`);
    if (refresh_token) {
      envContent = envContent.replace(/REFRESH_TOKEN=.*/, `REFRESH_TOKEN=${refresh_token}`);
    }
    await fs.writeFile(envPath, envContent);
    console.log('🔄 Token refreshed successfully');
    return access_token;  // Returns new access token
  } catch (error) {
    console.error('❌ Refresh token failed:', error.response?.data?.error || error.message);
    throw new Error('Failed to refresh token. Re-authenticate manually at https://www.upwork.com/developer/apps');
  }
}

let isPipelineRunning = false;
let assistantReady = false;

async function ensureAssistantReady() {
  if (assistantReady) return true;

  try {
    console.log('🔍 Checking assistant status...');
    let assistantId = getAssistantId();

    if (!assistantId) {
      console.log('🔄 Initializing assistant...');
      assistantId = await initializeAssistant();
    }

    if (!assistantId) {
      throw new Error('Assistant initialization failed');
    }

    console.log(`✅ Assistant ready (ID: ${assistantId})`);
    assistantReady = true;
    return true;
  } catch (err) {
    console.error('❌ Assistant preparation failed:', err);
    throw err;
  }
}

// GraphQL query for marketplaceJobPostingsSearch
// Updated GraphQL query - minimal valid structure from examples
// Updated GraphQL query - minimal valid structure (no pagination args)
const query = `
  query marketplaceJobPostingsSearch(
    $marketPlaceJobFilter: MarketplaceJobPostingsSearchFilter,
    $searchType: MarketplaceJobPostingSearchType,
    $sortAttributes: [MarketplaceJobPostingSearchSortAttribute]
  ) {
    marketplaceJobPostingsSearch(
      marketPlaceJobFilter: $marketPlaceJobFilter,
      searchType: $searchType,
      sortAttributes: $sortAttributes
    ) {
      totalCount
      edges {
        node {
          id
          title
          description
          createdDateTime
          amount {
            currency
            rawValue
          }
          skills {
            name
          }
          client {
            location {
              country
            }
          }
          category
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

async function fetchLatestJobs() {
  const now = new Date();
  console.log(`\n⏰ Starting job fetch at ${now.toISOString()}`);

  try {
    // Minimal variables - only supported filter: searchTerm_eq (broad "AI")
    // No pagination (unsupported via filter/arg) - default ~10 recent jobs
    const variables = {
      marketPlaceJobFilter: {
        searchTerm_eq: { andTerms_all: 'AI' },  // Broad keyword; use '' for all recent jobs
      },
      searchType: 'USER_JOBS_SEARCH',
      sortAttributes: [{ field: 'RECENCY' }],  // Newest first
    };

    const envPath = path.resolve(__dirname, '.env');
    const envConfig = dotenv.parse(await fs.readFile(envPath));
    let accessToken = envConfig.ACCESS_TOKEN;
    const refreshToken = envConfig.REFRESH_TOKEN;
    const clientId = envConfig.CLIENT_ID;
    const clientSecret = envConfig.CLIENT_SECRET;

    if (!accessToken || !refreshToken || !clientId || !clientSecret) {
      throw new Error('Missing ACCESS_TOKEN, REFRESH_TOKEN, CLIENT_ID, or CLIENT_SECRET in .env');
    }

    const doRequest = async (token) => axios.post(
      'https://api.upwork.com/graphql',
      { query, variables },
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        timeout: 10000,
      }
    );

    let response;
    try {
      response = await doRequest(accessToken);
    } catch (err) {
      console.error('Full API error response:', JSON.stringify(err.response?.data, null, 2));
      if (err.response?.status === 401) {
        console.error('⚠️ Access token invalid. Attempting to refresh via tokenManager...');
        const tm = require('./tokenManager');
        const newAccess = await tm();
        if (!newAccess) throw err;
        accessToken = newAccess;
        response = await doRequest(accessToken);
      } else {
        throw err;
      }
    }

    // Log full response for initial debugging (comment out after testing)
    // console.log('Full GraphQL response:', JSON.stringify(response.data, null, 2));

    const data = response.data.data?.marketplaceJobPostingsSearch;
    const errors = response.data.errors;
    if (errors && errors.length > 0) {
      throw new Error(`GraphQL errors: ${JSON.stringify(errors, null, 2)}. Check scopes (need 'Read marketplace Job Postings - Public').`);
    }
    if (!data || !data.edges || data.edges.length === 0) {
      console.log('No jobs found - try empty searchTerm_eq: { andTerms_all: "" } or check API scopes.');
      return 0;
    }

    const jobs = data.edges.map(edge => edge.node);
    console.log(`📄 Fetched ${jobs.length} jobs (total available: ${data.totalCount})`);

    // Post-filter: recent 24h (allow all countries and budgets)
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    const filteredJobs = jobs.filter(job => {
      const createdDate = new Date(job.createdDateTime);
      const isRecent = createdDate > oneDayAgo;
      return isRecent;
    });

    console.log(`📄 After post-filter (recent only): ${filteredJobs.length} jobs`);

    for (const job of filteredJobs) {
      try {
        const budget = job.amount ? `${job.amount.currency} ${job.amount.rawValue}` : 'Unknown';

        // DB insert with available fields; fallback if extras missing
        let insertResult;
        try {
          insertResult = await db.query(
            `INSERT INTO upwork_jobs (job_id, title, job_data, inserted_at, proposal_generated, client_country, budget)
             VALUES ($1, $2, $3, NOW(), FALSE, $4, $5)
             ON CONFLICT (job_id) DO NOTHING
             RETURNING id`,
            [
              job.id,
              job.title,
              JSON.stringify(job),
              job.client?.location?.country || null,
              budget
            ]
          );
        } catch (colErr) {
          console.warn('Extended columns missing; using basic insert:', colErr.message);
          insertResult = await db.query(
            `INSERT INTO upwork_jobs (job_id, title, job_data, inserted_at, proposal_generated)
             VALUES ($1, $2, $3, NOW(), FALSE)
             ON CONFLICT (job_id) DO NOTHING
             RETURNING id`,
            [job.id, job.title, JSON.stringify(job)]
          );
        }
        if (insertResult.rowCount > 0) {
          console.log(`✅ Stored job: ${job.title.slice(0, 50)}... (Budget: ${budget}, Date: ${job.createdDateTime.slice(0, 10)})`);
        }
      } catch (dbError) {
        console.error('Database insertion error:', dbError.message);
      }
    }

    console.log(`\n🎉 Successfully processed ${filteredJobs.length} jobs`);
    return filteredJobs.length;
  } catch (error) {
    console.error('\n❌ Error in job processing:', error.message);
    throw error;
  }
}

async function generateProposal(job, job_id) {
  try {
    await ensureAssistantReady();
    const assistantId = getAssistantId();
    if (!assistantId) throw new Error('Assistant ID not available');

    const skills = Array.isArray(job?.skills)
      ? job.skills.map(s => s.name || s.prettyName || '').filter(Boolean)
      : [];
    const title = job?.title || 'Unknown Title';
    const job_id_final = job_id || job?.id || job?.job_id || null; // Upwork job_id (text)
    const description = job?.description || '';
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
async function processNewJobs() {
  console.log('\n⏰ Starting proposal generation for new jobs...');
  try {
    const result = await db.query(
      `SELECT id, job_id, job_data 
       FROM upwork_jobs 
       WHERE proposal_generated = FALSE 
       ORDER BY inserted_at ASC 
       LIMIT 10`
    );

    let processedCount = 0;
    const jobs = result.rows;

    console.log(`📄 Found ${jobs.length} jobs to process`);
    for (const row of jobs) {
      try {
        const job = row.job_data;
        console.log(`Processing job ID: ${row.id}, Title: ${job.title || 'Unknown'}`);
        const genResult = await generateProposal(job, row.job_id);

        // Respect 80% threshold: skip downstream writes and DO NOT mark as processed if low score or missing profile
        if (genResult.relevance !== 'Yes' || !genResult.profile_id || (genResult.score ?? 0) < 80) {
          console.log(`↪️  Skipped job ${row.id} due to low score (${genResult.score || 0}) or missing profile (left unprocessed)`);
          continue;
        }

        let res=await db.query(
          `UPDATE upwork_jobs 
           SET proposal_generated = TRUE
           WHERE job_id = $1 returning proposal_generated`,
          [row.job_id]
        );
        
        processedCount++;
      } catch (err) {
        console.error(`❌ Failed to process job ${row.id || 'unknown'}:`, err.message);
      }
    }

    console.log(`\n🎉 Processed ${processedCount} jobs successfully`);
    return processedCount;
  } catch (err) {
    console.error('❌ Job processing failed:', err.message);
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

    console.log('\n🚀 Starting job pipeline...');
    const fetchedCount = await fetchLatestJobs();
    const processedCount = await processNewJobs();

    console.log(`\n🏁 Pipeline completed. Fetched: ${fetchedCount}, Processed: ${processedCount}`);
    console.log(`\n🏁 Pipeline completed. Processed: ${processedCount}`);
  } catch (err) {
    console.error('❌ Pipeline failed:', err.message);
  } finally {
    isPipelineRunning = false;
  }
}

async function startApplication() {
  try {
    console.log('🚀 Starting Upwork Job Processor (Node-only)...');

    // Initialize assistant
    await ensureAssistantReady();

    // Initial run
    await runJobPipeline();

    // Schedule regular runs
    cron.schedule('*/5 * * * *', () => {
      console.log('\n⏰ Scheduled run triggered');
      runJobPipeline().catch(console.error);
    });

    console.log('\n🟢 System ready and scheduled');
  } catch (startupError) {
    console.error('❌ Startup failed:', startupError.message);
    process.exit(1);
  }
}

// Start the application
startApplication();

// Keep process alive
process.stdin.resume();

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n🛑 Received shutdown signal...');
  try {
    await db.end();
    console.log('✅ Database connection closed');
    process.exit(0);
  } catch (err) {
    console.error('❌ Shutdown error:', err);
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