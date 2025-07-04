const express = require('express');
const router = express.Router();
const {generatePptx} = require('../controllers/pptxController');
console.log('PPTX Routes Loaded');

router.post('/generate-pptx', generatePptx);


module.exports = router;
