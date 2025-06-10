const express = require('express');
const cors = require('cors');
const fetchJobs = require('./upworkFetcher');
const refreshToken = require('./tokenManager');
const app = express();
const port = 3009;


// const jobRoutes = require('./routes/jobRoutes');
const jobProfileRoutes = require('./routes/jobProfileRoutes');
const profileRoutes = require('./routes/profiles');
const jobsRoutes = require('./routes/upworkJobsRoutes');
const queryRoutes = require("./routes/queryRoutes");

app.use(cors());
app.use(express.json());



// Routes
// app.use('/api/jobs', jobRoutes);
app.use('/api/job-profiles', jobProfileRoutes);
app.use('/api/profiles', profileRoutes);
app.use('/api/jobs', jobsRoutes);
app.use('/api',queryRoutes);


const initialize = async () => {
  const accessToken = await refreshToken(); // Refresh at start
  if (accessToken) {
    fetchJobs(); // Only call if token is fresh
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
