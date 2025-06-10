const express = require('express');
const router = express.Router();
const proposalController = require('../controllers/proposalController');

router.get('/:profile_id', proposalController.getProposalById);
router.delete('/:id', proposalController.deleteProposal);

module.exports = router;