const db = require('../db');

// GET all job_profile entries
const getAllJobProfiles = async (req, res) => {
    try {
        const companyId = req.user?.company_id;
        if (!companyId) return res.status(401).json({ message: 'Missing company scope' });
        const result = await db.query(`
            SELECT 
                jp.*, 
                j.job_data->>'department' AS department
            FROM 
                job_profile jp
            JOIN 
                upwork_jobs j ON jp.job_id = j.id
            JOIN profiles p ON p.id = jp.profile_id
            WHERE p.company_id = $1
        `, [companyId]);
        res.status(200).json(result.rows);
    } catch (error) {
        res.status(500).json({ message: 'Error fetching job profiles', error: error.message });
    }
};

// GET a specific job_profile entry by job_id and profile_id
const getJobProfileById = async (req, res) => {
    const { profile_id } = req.params;
    try {
        const companyId = req.user?.company_id;
        if (!companyId) return res.status(401).json({ status: 401, message: 'Missing company scope' });
        const result = await db.query(`
            SELECT 
                jp.*,
                uj.title as job_title,
                uj.job_data
            FROM 
                job_profile jp
            LEFT JOIN 
                upwork_jobs uj ON jp.job_id = uj.id
            WHERE 
                jp.profile_id = $1 AND EXISTS (SELECT 1 FROM profiles p WHERE p.id = jp.profile_id AND p.company_id = $2)
        `, [profile_id, companyId]);

        if (result.rows.length === 0) {
            return res.status(404).json({
                status: 404, 
                message: 'Job profile not found'
            });
        }

        res.status(200).json({
            status: 200,
            message: 'Job profiles retrieved successfully',
            data: result.rows
        });
    } catch (error) {
        res.status(500).json({
            status: 500, 
            message: 'Error fetching job profile', 
            error: error.message
        });
    }
};

// CREATE job_profile entry
const createJobProfile = async (req, res) => {
    const { job_id, profile_id, can_apply, probability } = req.body;
    const companyId = req.user?.company_id;
    if (!companyId) return res.status(401).json({ message: 'Missing company scope' });
    if (!job_id || !profile_id || can_apply == null || probability == null) {
        return res.status(400).json({ message: 'Missing required fields' });
    }

    try {
        const ok = await db.query('SELECT 1 FROM profiles WHERE id = $1 AND company_id = $2', [profile_id, companyId]);
        if (ok.rows.length === 0) return res.status(404).json({ message: 'Profile not found' });
        const insertQuery = `INSERT INTO job_profile (job_id, profile_id, can_apply, probability) VALUES ($1, $2, $3, $4) RETURNING *`;
        const result = await db.query(insertQuery, [job_id, profile_id, can_apply, probability]);
        res.status(201).json({ message: 'Job profile created', data: result.rows[0] });
    } catch (error) {
        res.status(500).json({ message: 'Error creating job profile', error: error.message });
    }
};

// UPDATE job_profile
const updateJobProfile = async (req, res) => {
    const { job_id, profile_id } = req.params;
    const companyId = req.user?.company_id;
    if (!companyId) return res.status(401).json({ message: 'Missing company scope' });
    const { can_apply, probability } = req.body;

    try {
        const ok = await db.query('SELECT 1 FROM profiles WHERE id = $1 AND company_id = $2', [profile_id, companyId]);
        if (ok.rows.length === 0) return res.status(404).json({ message: 'Profile not found' });
        const updateQuery = `UPDATE job_profile SET can_apply = $1, probability = $2 WHERE job_id = $3 AND profile_id = $4 RETURNING *;`;
        const result = await db.query(updateQuery, [can_apply, probability, job_id, profile_id]);
        if (result.rowCount === 0) {
            return res.status(404).json({ message: 'Job profile not found' });
        }
        res.status(200).json({ message: 'Job profile updated', data: result.rows[0] });
    } catch (error) {
        res.status(500).json({ message: 'Error updating job profile', error: error.message });
    }
};

// DELETE job_profile
const deleteJobProfile = async (req, res) => {
    const { job_id, profile_id } = req.params;
    const companyId = req.user?.company_id;
    if (!companyId) return res.status(401).json({ message: 'Missing company scope' });
    try {
        const ok = await db.query('SELECT 1 FROM profiles WHERE id = $1 AND company_id = $2', [profile_id, companyId]);
        if (ok.rows.length === 0) return res.status(404).json({ message: 'Profile not found' });
        const deleteQuery = 'DELETE FROM job_profile WHERE job_id = $1 AND profile_id = $2 RETURNING *;';
        const result = await db.query(deleteQuery, [job_id, profile_id]);
        if (result.rowCount === 0) {
            return res.status(404).json({ message: 'Job profile not found' });
        }
        res.status(200).json({ message: 'Job profile deleted', data: result.rows[0] });
    } catch (error) {
        res.status(500).json({ message: 'Error deleting job profile', error: error.message });
    }
};

module.exports = {
    getAllJobProfiles,
    getJobProfileById,
    createJobProfile,
    updateJobProfile,
    deleteJobProfile
};