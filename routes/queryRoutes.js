const express = require('express');
const router = express.Router();
const multer = require('multer');
const queryController = require('../controllers/queryController');

const upload = multer({ dest: 'Uploads/' });

router.post('/query', queryController.processQuery);
router.post('/train/:profileId', upload.single('pdf'), queryController.trainProfile);

module.exports = router;