const express = require("express");
const router = express.Router();
const path = require("path");
const profileController = require("../controllers/profilesController");

router.post("/", profileController.createProfile);
router.get("/", profileController.getProfiles);
router.delete("/:id", profileController.deleteProfile);
router.put('/disable-training/:profileId', profileController.allowTrainProfile);
router.put('/enable-training/:profileId', profileController.enableTrainProfile);

module.exports = router;
