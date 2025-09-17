const express = require('express');
const router = express.Router();
const chat = require('../controllers/chatController');

// Start or reuse a chat thread for a profile
router.post('/start/:profileId', chat.startChat);

// Get current thread and stored history for a profile
router.get('/history/:profileId', chat.getHistory);

// Post a message to a thread and get assistant reply
router.post('/message/:threadId', chat.postMessage);

// Edit a user message and regenerate continuation
router.put('/message/:messageId', chat.editMessage);

// Save encrypted message(s) (client-side encrypted)
router.post('/encrypted/:threadId', chat.saveEncrypted);

module.exports = router;


