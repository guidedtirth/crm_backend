const pool = require('../db');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');

exports.signup = async (req, res) => {
    const { username, email, password, confirmPassword } = req.body;

    try {
        const userCheck = await pool.query('SELECT * FROM users WHERE email = $1', [email]);
        if (userCheck.rows.length > 0) {
            return res.json({ status: 409, message: 'Email already exists' });
        }

        const hashedPassword = await bcrypt.hash(password, 10);

        await pool.query(
            'INSERT INTO users (username, email, password) VALUES ($1, $2, $3)',
            [username, email, hashedPassword]
        );

        res.json({ status: 200, message: 'User registered successfully' });
    } catch (error) {
        res.status(500).json({ message: 'Signup failed', error: error.message });
    }
};

exports.login = async (req, res) => {
    const { email, password } = req.body;

    try {
        const userResult = await pool.query('SELECT * FROM users WHERE email = $1', [email]);
        const user = userResult.rows[0];

        if (!user) {
            return res.json({ status: 404, message: 'User does not exist or Wrong Email' });
        }

        const isMatch = await bcrypt.compare(password, user.password);
        if (!isMatch) {
            return res.json({ status: 402, message: 'Invalid password' });
        }

        const token = jwt.sign({ id: user.id }, 'your_jwt_secret');

        res.status(200).json({ message: 'Login successful', token, data: { id: user.id, username: user.username, email: user.email } });
    } catch (error) {
        res.status(500).json({ message: 'Login failed', error: error.message });
    }
};
exports.varifyToken =async (req, res) => {
    const { token } = req.params;

    try {
        // 1. Verify JWT token
        const decoded = jwt.verify(token, 'your_jwt_secret');
        const userId = decoded.id;

        // 2. Query the user from the 'users' table
        const result = await pool.query(
            'SELECT id, username, email FROM users WHERE id = $1',
            [userId]
        );

        const user = result.rows[0];

        if (!user) {
            return res.status(404).json({ message: 'User not found' });
        }

        // 3. Return user info (excluding password)
        return res.status(200).json({ user });

    } catch (error) {
        return res.status(401).json({ message: 'Invalid or expired token' });
    }
}