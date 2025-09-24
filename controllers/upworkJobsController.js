const db = require('../db');

module.exports = {
  // Get all jobs
  getAllJobs: async (req, res) => {
    try {
      const companyId = req.user?.company_id;
      if (!companyId) return res.status(401).json({ error: 'Missing company scope' });
      const { rows } = await db.query(`
        SELECT uj.*
        FROM upwork_jobs uj
        ORDER BY uj.inserted_at DESC
        LIMIT 100
      `);
      res.json(rows);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  },

  // Get single job
  getJob: async (req, res) => {
    try {
      const { rows } = await db.query('SELECT * FROM upwork_jobs WHERE id = $1', [req.params.id]);
      if (rows.length === 0) {
        return res.status(404).json({ error: 'Job not found' });
      }
      res.json(rows[0]);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  },


  // Delete job
  deleteJob: async (req, res) => {
    try {
      const { rows } = await db.query(
        'DELETE FROM upwork_jobs WHERE id = $1 RETURNING *',
        [req.params.id]
      );
      if (rows.length === 0) {
        return res.status(404).json({ error: 'Job not found' });
      }
      res.json({ message: 'Job deleted successfully' });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  },

  // Search jobs
  searchJobs: async (req, res) => {
    const searchTerm = req.query.q || '';
    try {
      const { rows } = await db.query(
        'SELECT * FROM upwork_jobs WHERE title ILIKE $1 ORDER BY inserted_at DESC',
        [`%${searchTerm}%`]
      );
      res.json(rows);
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  }
};