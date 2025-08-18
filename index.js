const express = require('express');
const cors = require('cors');
const fs = require('fs').promises;
const bodyParser = require('body-parser');
const fetchJobs = require('./upworkFetcher');
const { initializeAssistant } = require('./assistant');
const refreshToken = require('./tokenManager');
const app = express();
const port = 3009;
const path = require('path');
const PYTHON_EXECUTABLE = process.platform === 'win32'
  ? path.join(__dirname, '.venv', 'Scripts', 'python.exe') // Windows
  : path.join(__dirname, '.venv', 'bin', 'python3');       // Linux/Mac


// Initialize Assistant
initializeAssistant().catch(err => {
  console.error('Failed to initialize assistant:', err);
  process.exit(1);
});



// const jobRoutes = require('./routes/jobRoutes');
const jobProfileRoutes = require('./routes/jobProfileRoutes');
const profileRoutes = require('./routes/profiles');
const jobsRoutes = require('./routes/upworkJobsRoutes');
const queryRoutes = require("./routes/queryRoutes");
const authRoutes = require('./routes/authRoutes');
const proposalRoutes = require('./routes/proposalRoutes');
const pptxRoutes = require('./routes/pptxRoutes');
app.use(bodyParser.json({ limit: '5mb' }));

app.use(cors());
app.use(express.json());



// Routes
// app.use('/api/jobs', jobRoutes);
app.use('/api/job-profiles', jobProfileRoutes);
app.use('/api/profiles', profileRoutes);
app.use('/api/jobs', jobsRoutes);
app.use('/api',queryRoutes);
app.use('/api/proposal', proposalRoutes);
app.use('/api/auth', authRoutes);

app.use('/apis', pptxRoutes);


const initialize = async () => {
  const accessToken = await refreshToken(); // Refresh at start
  if (accessToken) {
   await fetchJobs(); // Only call if token is fresh
  }

  // Schedule refresh every 23 hours (before 24 hour expiry)
  setInterval(async () => {
    const newToken = await refreshToken();
    if (newToken) {
      console.log('🔄 Token refreshed successfully');
    }
  }, 23 * 60 * 60 * 1000); // 23 hours
};

initialize();

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('Shutting down server');
  process.exit(0);
});

// Update the Python executable path check
fs.access(PYTHON_EXECUTABLE)
  .then(() => {
    console.log(`Python executable found at: ${PYTHON_EXECUTABLE}`);
  })
  .catch(() => {
    console.error(`Error: Python executable not found at ${PYTHON_EXECUTABLE}`);
    process.exit(1);
  });
