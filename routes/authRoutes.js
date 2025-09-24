// Auth Routes
// Uses verifyToken (preferred) with fallback to legacy varifyToken export
const express = require('express');
const router = express.Router();
const { signup, login, verifyToken } = require('../controllers/authController');

router.post('/signup', signup);
router.post('/login', login);
router.get('/verify/:token', verifyToken);

module.exports = router;
