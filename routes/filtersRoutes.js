const express = require('express');
const router = express.Router();
const { getFilters, saveFilters } = require('../controllers/filtersController');

router.get('/', getFilters);
router.post('/', saveFilters);

module.exports = router;


