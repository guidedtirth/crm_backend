const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');
const { exec } = require('child_process');
const { v4: uuidv4 } = require('uuid');
const dotenv = require('dotenv');
const cron = require('node-cron');
const { getAssistantId, PYTHON_EXECUTABLE, initializeAssistant } = require('./assistant');
const db = require('./db');
const util = require('util');

// Promisify exec for async/await
const execAsync = util.promisify(exec);

// Load environment variables
dotenv.config();

// GraphQL query for Upwork jobs
const query = `
  query {
    marketplaceJobPostings(
      marketPlaceJobFilter: {
        searchExpression_eq: "AI",
        budgetRange_eq: {
          rangeStart: 1000
        }
      }
    ) {
      totalCount
      edges {
        node {
          id
          title
          description
          experienceLevel
          publishedDateTime
          category
          recordNumber
          client {
            location {
              city
              country
              timezone
            }
          }
          occupations {
            category {
              id
              prefLabel
            }
          }
          skills {
            name
            prettyName
            highlighted
          }
          preferredFreelancerLocation
          amount {
            currency
            rawValue
          }
          hourlyBudgetType
          hourlyBudgetMin {
            currency
            rawValue
          }
          hourlyBudgetMax {
            currency
            rawValue
          }
          totalApplicants
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

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

async function fetchLatestJobs() {
  const now = new Date();
  console.log(`\n⏰ Starting job fetch at ${now.toISOString()}`);

  try {
    const variables = {
      marketPlaceJobFilter: {
        jobPostingAccess: 'PUBLIC_INDEX',
        daysPosted_eq: 0,
        postedOn_gt: new Date(Date.now() - 6 * 60 * 1000).toISOString(),
      },
      pagination: { first: 10, after: null },
    };

    const envPath = path.resolve(__dirname, '.env');
    const envConfig = dotenv.parse(await fs.readFile(envPath));
    const accessToken = envConfig.ACCESS_TOKEN;

    if (!accessToken) {
      throw new Error('Missing ACCESS_TOKEN in environment');
    }

    const response = await axios.post(
      'https://api.upwork.com/graphql',
      { query, variables },
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        timeout: 10000,
      }
    );

    if (!response.data?.data?.marketplaceJobPostings) {
      throw new Error('Invalid API response structure');
    }

    const data = response.data.data.marketplaceJobPostings;
    console.log(`📄 Found ${data.edges.length} new jobs`);

    for (const edge of data.edges) {
      const job = edge.node;
      try {
        const insertResult = await db.query(
          `INSERT INTO upwork_jobs (job_id, title, job_data, inserted_at, proposal_generated) 
           VALUES ($1, $2, $3, NOW(), FALSE) 
           ON CONFLICT (job_id) DO NOTHING
           RETURNING id`,
          [job.id, job.title, job]
        );

        if (insertResult.rowCount > 0) {
          console.log(`✅ Stored job: ${job.title.slice(0, 50)}...`);
        }
      } catch (dbError) {
        console.error('Database insertion error:', dbError.message);
      }
    }

    console.log(`\n🎉 Successfully processed ${data.edges.length} jobs`);
    return data.edges.length;
  } catch (error) {
    console.error('\n❌ Error in job processing:', error.message);
    if (error.response?.status === 401) {
      console.error('⚠️ Token expired or invalid. Get a new one from Upwork.');
    }
    throw error;
  }
}

async function generateProposal(job) {
  console.log(`\n🔍 Generating proposal for job ID: `,job);
  try {
    await ensureAssistantReady();
    const assistantId = getAssistantId();

    if (!assistantId) {
      throw new Error('Assistant ID not available');
    }

    const jobId = job.id || job.job_id;
    console.log(`\n🔍 Generating proposal for job ${jobId}: ${job.title?.slice(0, 50)}...`);

    // Create temp directory if needed
    const tempDir = path.join(__dirname, '..', 'temp');
    try {
      await fs.access(tempDir);
    } catch {
      console.log('Creating temp directory:', tempDir);
      await fs.mkdir(tempDir, { recursive: true });
    }

    // Prepare query data
    const skills = Array.isArray(job.skills)
      ? job.skills.map(skill => skill.name || skill.prettyName || '').filter(Boolean)
      : [];
    const queryData = {
      title: job || 'Unknown Title',
      description: job.description || '',
      skills: skills,
      budgetMin: 150,
      budgetMax: 1000,
      assistantId: assistantId,
    };

    // console.log('Query data prepared:', JSON.stringify(queryData, null, 2));

    // Write query to temp file
    const queryFile = path.join(tempDir, `query_${uuidv4()}.json`);
    // console.log('Writing query file to:', queryFile);
    await fs.writeFile(queryFile, JSON.stringify(queryData));

    // Execute Python script
    const pythonScript = path.join(__dirname, 'query_assistant.py');
    const command = `"${PYTHON_EXECUTABLE}" "${pythonScript}" "${queryFile}"`;
    console.log(`⚙️ Executing: ${command}`);

    const { stdout, stderr } = await execAsync(command, {
      maxBuffer: 1024 * 1024 * 5, // 5MB buffer
      timeout: 120000 // 2 minute timeout
    });

    // Handle script output
    if (stderr && (stderr.includes('Error:') || stderr.includes('Exception'))) {
      console.error('Script stderr:', stderr);
      throw new Error(stderr);
    }

    const result = JSON.parse(stdout);

    // Clean up
    console.log('Attempting to delete file:', queryFile);
    try {
      await fs.access(queryFile); // Verify file exists
      await fs.unlink(queryFile);
      // console.log('Successfully deleted temp file:', queryFile);
    } catch (err) {
      console.warn('⚠️ Could not delete temp file:', err.message, err.code);
    }

    return result;
  } catch (err) {
    console.error(`❌ Proposal generation failed for job ${job.id || job.job_id}:`, err.message);
    throw err;
  }
}

async function processNewJobs() {
  console.log('\n⏰ Starting proposal generation for new jobs...');
  try {
    const result = await db.query(
      `SELECT id, job_data 
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
        const result = await generateProposal(job);

        let res=await db.query(
          `UPDATE upwork_jobs 
           SET proposal_generated = TRUE
           WHERE id = $1 returning proposal_generated`,
          [row.id]
        );
        console.log("resulr",res)

        console.log(`✅ Generated proposal for job ${row.id}`);
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
    // const fetchedCount = await fetchLatestJobs();
    const processedCount = await processNewJobs();

    // console.log(`\n🏁 Pipeline completed. Fetched: ${fetchedCount}, Processed: ${processedCount}`);
    console.log(`\n🏁 Pipeline completed. Processed: ${processedCount}`);
  } catch (err) {
    console.error('❌ Pipeline failed:', err.message);
  } finally {
    isPipelineRunning = false;
  }
}

async function startApplication() {
  try {
    console.log('🚀 Starting Upwork Job Processor...');
    console.log(`Python executable: ${PYTHON_EXECUTABLE}`);

    // Verify environment
    try {
      await fs.access(PYTHON_EXECUTABLE);
      console.log('✅ Python executable verified');
    } catch {
      throw new Error(`Python executable not found at ${PYTHON_EXECUTABLE}`);
    }

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