const express = require('express');
const router = express.Router();
const { signup, login, varifyToken } = require('../controllers/authController');

router.post('/signup', signup);
router.post('/login', login);
router.get('/verify/:token', varifyToken);

module.exports = router;
