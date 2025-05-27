const express = require('express');
const router = express.Router();
const jobProfileController = require('../controllers/jobProfileController');

router.get('/', jobProfileController.getAllJobProfiles);
router.get('/:profile_id', jobProfileController.getJobProfileById);
router.post('/', jobProfileController.createJobProfile);
router.put('/:job_id/:profile_id', jobProfileController.updateJobProfile);
router.delete('/:job_id/:profile_id', jobProfileController.deleteJobProfile);

module.exports = router;