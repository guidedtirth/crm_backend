const db = require('../db');
console.log('jobController.js loaded');

// GET all jobs
const getAllJobs = async (req, res) => {
  console.log('getAllJobs called');
  try {
    const result = await db.query('SELECT id, job_id, job_data FROM jobs');
    res.status(200).json(result.rows || []);
  } catch (error) {
    res.status(500).json({ message: 'Error fetching jobs', error: error.message });
  }
};

// GET job by ID
// const getJobById = async (req, res) => {
//   try {
//     const { id } = req.params;
//     const result = await db.query('SELECT * FROM jobs WHERE id = $1', [id]);

//     if (result.rows.length === 0) {
//       return res.status(404).json({ message: 'Job not found' });
//     }

//     res.status(200).json(result.rows[0]);
//   } catch (err) {
//     res.status(500).json({ error: err.message });
//   }
// };
const getJobById = async (req, res) => {
  try {
    const { id } = req.params;
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(id)) {
      return res.status(400).json({ message: 'Invalid job ID format (UUID expected)' });
    }

    const queryText = 'SELECT * FROM jobs WHERE id = $1';
    const queryParams = [id];

    const result = await db.query(queryText, queryParams);

    if (result.rows.length === 0) {
      return res.status(404).json({ message: 'Job not found' });
    }

    return res.status(200).json({
      message: 'Job retrieved successfully',
      job: result.rows[0],
    });
  } catch (err) {
    console.error('Error fetching job by ID:', err);
    return res.status(500).json({ message: 'Internal server error' });
  }
};


// CREATE jobs (bulk insert)
const createJob = async (req, res) => {
  try {
    if (!req.body || !Array.isArray(req.body) || req.body.length === 0) {
      return res.status(400).json({ error: 'Expected a non-empty array of job listings' });
    }

    const insertJobQuery = `INSERT INTO jobs (job_id, job_data) VALUES ($1, $2)`;

    for (const job of req.body) {
      if (!job.job_id || !job.job_data) {
        return res.status(400).json({ error: 'Each job must contain job_id and job_data' });
      }

      await db.query(insertJobQuery, [job.job_id, JSON.stringify(job.job_data)]);
    }

    res.status(201).json({ message: 'Jobs inserted successfully' });
  } catch (error) {
    res.status(500).json({ message: 'Error inserting jobs', error: error.message });
  }
};

// UPDATE a job by ID
const updateJob = async (req, res) => {
  try {
    const { id } = req.params;
    const { job_id, job_data } = req.body;

    const updateQuery = `
      UPDATE jobs
      SET job_id = $1, job_data = $2
      WHERE id = $3
      RETURNING *;
    `;

    const result = await db.query(updateQuery, [job_id, JSON.stringify(job_data), id]);

    if (result.rowCount === 0) {
      return res.status(404).json({ message: 'Job not found' });
    }

    res.status(200).json({ message: 'Job updated', job: result.rows[0] });
  } catch (error) {
    res.status(500).json({ message: 'Error updating job', error: error.message });
  }
};

// DELETE a job by ID
const deleteJob = async (req, res) => {
  try {
    const { id } = req.params;

    const deleteQuery = 'DELETE FROM jobs WHERE id = $1 RETURNING *;';
    const result = await db.query(deleteQuery, [id]);

    if (result.rowCount === 0) {
      return res.status(404).json({ message: 'Job not found' });
    }

    res.status(200).json({ message: 'Job deleted', job: result.rows[0] });
  } catch (error) {
    res.status(500).json({ message: 'Error deleting job', error: error.message });
  }
};

// Export all controllers together
module.exports = {
  getAllJobs,
  getJobById,
  createJob,
  updateJob,
  deleteJob
};
