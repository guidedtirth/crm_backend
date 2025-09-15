const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const queryController = require('../controllers/queryController');

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, 'Uploads/'),
  filename: (_req, file, cb) => {
    const safeBase = path.parse(file.originalname).name.replace(/[^a-zA-Z0-9._-]/g, '_');
    const ext = path.extname(file.originalname).toLowerCase();
    cb(null, `${Date.now()}_${safeBase}${ext}`);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: 8 * 1024 * 1024 }, // 8MB
  fileFilter: (_req, file, cb) => {
    const allowed = ['.pdf', '.docx', '.txt'];
    const ext = path.extname(file.originalname).toLowerCase();
    if (!allowed.includes(ext)) return cb(new Error('Unsupported file type'));
    cb(null, true);
  }
});

router.post('/query', queryController.processQuery);
router.post('/train/:profileId', upload.any(), queryController.trainProfile);

module.exports = router;