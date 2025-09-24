const express = require('express');
const router = express.Router();
const jobsController = require('../controllers/upworkJobsController');

// CRUD routes
router.get('/', jobsController.getAllJobs);
router.get('/:id', jobsController.getJob);
router.delete('/:id', jobsController.deleteJob);

// Search route
router.get('/search', jobsController.searchJobs);

module.exports = router;