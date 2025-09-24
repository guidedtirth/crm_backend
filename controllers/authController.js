/**
 * Auth Controller
 * Company signup/login and token verification (company-scoped JWT)
 */
const pool = require('../db');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { v4: uuidv4 } = require('uuid');

/** Register a company (id = company_id), attach email/password */
exports.signup = async (req, res) => {
    const { companyName, email, password, confirmPassword } = req.body || {};
    try {
        if (!companyName || !email || !password || !confirmPassword) {
            return res.status(400).json({ message: 'companyName, email, password and confirmPassword are required' });
        }
        if (password !== confirmPassword) {
            return res.status(400).json({ message: 'Passwords do not match' });
        }

        // Find or create company; attach creds to company
        let company = await pool.query('SELECT id, email FROM companies WHERE name = $1', [companyName]);
        let companyId;
        const hashedPassword = await bcrypt.hash(password, 10);
        if (company.rows.length === 0) {
            companyId = uuidv4();
            await pool.query('INSERT INTO companies (id, name, email, password) VALUES ($1, $2, $3, $4)', [companyId, companyName, email, hashedPassword]);
        } else {
            companyId = company.rows[0].id;
            // If company exists and already has same email, block
            if (company.rows[0].email && company.rows[0].email === email) {
                return res.status(409).json({ status: 409, message: 'Email already exists for this company' });
            }
            await pool.query('UPDATE companies SET email = $1, password = $2 WHERE id = $3', [email, hashedPassword, companyId]);
        }

        const token = jwt.sign({ id: companyId, company_id: companyId }, process.env.JWT_SECRET || 'your_jwt_secret');
        res.json({ status: 200, message: 'Company registered successfully', token, company_id: companyId });
    } catch (error) {
        res.status(500).json({ message: 'Signup failed', error: error.message });
    }
};

/** Login for an existing company (email/password on companies row) */
exports.login = async (req, res) => {
    const { companyName, email, password } = req.body || {};
    try {
        if (!companyName || !email || !password) {
            return res.status(400).json({ message: 'companyName, email and password are required' });
        }
        const company = await pool.query('SELECT id, email, password FROM companies WHERE name = $1', [companyName]);
        if (company.rows.length === 0) {
            return res.status(404).json({ status: 404, message: 'Company not found' });
        }
        const row = company.rows[0];
        if (!row.email || !row.password || row.email !== email) {
            return res.status(404).json({ status: 404, message: 'Login not configured for this company or wrong email' });
        }
        const isMatch = await bcrypt.compare(password, row.password);
        if (!isMatch) {
            return res.status(402).json({ status: 402, message: 'Invalid password' });
        }
        const token = jwt.sign({ id: row.id, company_id: row.id }, process.env.JWT_SECRET || 'your_jwt_secret');
        res.status(200).json({ message: 'Login successful', token, company_id: row.id, data: { company_id: row.id, company_name: companyName, email } });
    } catch (error) {
        res.status(500).json({ message: 'Login failed', error: error.message });
    }
};
/** Verify JWT sent in path and return company info */
exports.verifyToken =async (req, res) => {
    const { token } = req.params;

    try {
        // 1. Verify JWT token
        const decoded = jwt.verify(token, process.env.JWT_SECRET || 'your_jwt_secret');
        const userId = decoded.id;
        const companyId = decoded.company_id;

        // 2. Return company info (no password)
        const result = await pool.query('SELECT id, name, email FROM companies WHERE id = $1', [companyId]);
        const company = result.rows[0];
        if (!company) return res.status(404).json({ message: 'Company not found' });
        return res.status(200).json({ company });

    } catch (error) {
        return res.status(401).json({ message: 'Invalid or expired token' });
    }
}