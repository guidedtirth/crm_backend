const axios = require('axios');
const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');
const db = require('./db');



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

const cron = require('node-cron');

async function fetchLatestJobs() {
  const now = new Date();
  console.log(`\n⏰ Starting job fetch at ${now.toISOString()}`);

  try {
    const variables = {
      marketPlaceJobFilter: {
        jobPostingAccess: 'PUBLIC_INDEX',
        daysPosted_eq: 0,
        postedOn_gt: new Date(Date.now() - 6 * 60 * 1000).toISOString()
      },
      pagination: {
        first: 10,
        after: null
      }
    };
    // console.log("token", process.env.ACCESS_TOKEN);
    const envPath = path.resolve(__dirname, '.env');
    const envConfig = dotenv.parse(fs.readFileSync(envPath));

    const accessToken = envConfig.ACCESS_TOKEN;
    const response = await axios.post(
      'https://api.upwork.com/graphql',
      { query, variables },
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        timeout: 10000
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
          `INSERT INTO upwork_jobs (job_id, title, job_data, inserted_at) 
           VALUES ($1, $2, $3, NOW()) 
           ON CONFLICT (job_id) DO NOTHING
           RETURNING id`,
          [job.id, job.title, job]
        );

        if (insertResult.rowCount > 0) {
          console.log(`✅ Stored job Tittle: ${job.title.slice(0, 50)}...`);
        }
      } catch (dbError) {
        console.error('Database insertion error:', dbError.message);
      }
    }

    console.log(`\n🎉 Successfully processed ${data.edges.length} jobs`);
  } catch (error) {
    console.error('\n❌ Error in job processing:', error.message);
    if (error.response?.status === 401) {
      console.error('⚠️ Token expired or invalid. Get a new one from Upwork.');
    }
  }
}

// Schedule job to run every 5 minutes
cron.schedule('*/5 * * * *', () => {
  console.log('\n⏰ Running scheduled job fetch...');
  fetchLatestJobs().catch(console.error);
});

// Initial run
console.log('🚀 Starting Upwork job fetcher...');
module.exports = fetchLatestJobs; // No parentheses

// Keep the process alive
process.stdin.resume();

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Received shutdown signal, closing database connection...');
  db.end()
    .then(() => process.exit(0))
    .catch(err => {
      console.error('Error closing database connection:', err);
      process.exit(1);
    });
});