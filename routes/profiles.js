const express = require("express");
const router = express.Router();
const multer = require("multer");
const path = require("path");
const profileController = require("../controllers/profilesController");

// Multer config
const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, "uploads/"),
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname);
    cb(null, `${req.params.id}-${Date.now()}${ext}`);
  },
});
const upload = multer({
  storage,
  fileFilter: (_req, file, cb) => {
    file.mimetype === "application/pdf"
      ? cb(null, true)
      : cb(new Error("Only PDFs allowed"), false);
  },
});

router.post("/", profileController.createProfile);
router.get("/", profileController.getProfiles);
router.put("/:id/train", upload.single("file"), profileController.trainProfile);
router.delete("/:id", profileController.deleteProfile);

module.exports = router;
