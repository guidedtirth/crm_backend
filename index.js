const express = require('express');
const cors = require('cors');
const fs = require('fs').promises;
const bodyParser = require('body-parser');
const { initializeAssistant } = require('./assistant');
const { refreshToken } = require('./platforms');
const app = express();
const port = 3009;
const path = require('path');
// Python no longer required; ensure Node-only flow


// Initialize Assistant
initializeAssistant().catch(err => {
  console.error('Failed to initialize assistant:', err);
  process.exit(1);
});



// const jobRoutes = require('./routes/jobRoutes');
const jobProfileRoutes = require('./routes/jobProfileRoutes');
const profileRoutes = require('./routes/profilesRoutes');
const jobsRoutes = require('./platforms/upwork/routes/upworkJobsRoutes');
const queryRoutes = require("./routes/queryRoutes");
const authRoutes = require('./routes/authRoutes');
const proposalRoutes = require('./routes/proposalRoutes');
const filtersRoutes = require('./routes/filtersRoutes');
const chatRoutes = require('./routes/chatRoutes');
const authMw = require('./middleware/auth');
const { ensureTenantSchema } = require('./tenant');
app.use(bodyParser.json({ limit: '5mb' }));

app.use(cors());
app.use(express.json());



// Routes
// app.use('/api/jobs', jobRoutes);
app.use('/api/auth', authRoutes); // public

// protected routes
app.use('/api/job-profiles', authMw, jobProfileRoutes);
app.use('/api/profiles', authMw, profileRoutes);
app.use('/api/jobs', authMw, jobsRoutes);
app.use('/api', authMw, queryRoutes);
app.use('/api/proposal', authMw, proposalRoutes);
app.use('/api/filters', authMw, filtersRoutes);
app.use('/api/chat', authMw, chatRoutes);

// Start platform pipelines via registry (Upwork self-initializes)
require('./platforms');


const initialize = async () => {
  const accessToken = await refreshToken(); // Refresh at start
  // upworkFetcher self-starts its scheduler; no direct call needed

  // Schedule refresh every 23 hours (before 24 hour expiry)
  setInterval(async () => {
    const newToken = await refreshToken();
    if (newToken) {
      console.log('🔄 Token refreshed successfully');
    }
  }, 23 * 60 * 60 * 1000); // 23 hours
};

initialize();

// Ensure tenant schema
ensureTenantSchema().catch((e) => console.error('Tenant schema init failed', e));

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('Shutting down server');
  process.exit(0);
});

// Removed Python executable checks; Node-only implementation
