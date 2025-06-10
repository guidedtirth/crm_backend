const pool = require("../db");
const pdfParse = require("pdf-parse");
const path = require("path");
const fs = require("fs").promises;
const util = require("util");
const exec = util.promisify(require("child_process").exec);

exports.createProfile = async (req, res) => {
  try {
    console.log("Creating profile with data:", req.body);
    const { name } = req.body;
    const result = await pool.query("INSERT INTO profiles (name) VALUES ($1) RETURNING *", [name]);

    res.json(result.rows[0]);
  } catch (err) {
    console.error(err.message);
    res.status(500).send("Server Error");
  }
};

exports.getProfiles = async (_req, res) => {
  try {
    const result = await pool.query("SELECT * FROM profiles ORDER BY last_updated DESC");
    res.json(result.rows);
  } catch (err) {
    console.error(err.message);
    res.status(500).send("Server Error");
  }
};


exports.deleteProfile = async (req, res) => {
  try {
    const { id } = req.params;

    // 1. Fetch training_file info for the profile
    const profileRes = await pool.query("SELECT training_file FROM profiles WHERE id = $1::uuid", [id]);
    
    if (profileRes.rows.length === 0) {
      return res.status(404).json({ error: 'Profile not found' });
    }

    const trainingFiles = profileRes.rows[0]?.training_file || [];

    // 2. Delete associated files from disk
    for (const file of trainingFiles) {
      if (file.path) { // Check if path exists
        try {
          await fs.access(file.path); // Check if file exists
          await fs.unlink(file.path);
          console.log(`Deleted file: ${file.path}`);
        } catch (err) {
          if (err.code === 'ENOENT') {
            console.warn(`File not found: ${file.path}`);
          } else {
            console.warn(`Error deleting file: ${file.path}`, err.message);
          }
        }
      } else {
        console.warn('File path is undefined for file:', file.name);
      }
    }

    // 3. Delete profile from DB
    await pool.query("DELETE FROM profiles WHERE id = $1::uuid", [id]);
    const result = await pool.query("DELETE FROM job_profile WHERE profile_id = $1 RETURNING *", [id]);

    res.json({ 
      message: "Profile and files deleted successfully",
      deletedProfileId: id,
      deletedFiles: trainingFiles.map(f => f.name),
      deletedJobProfiles: result.rows 
    });
  } catch (err) {
    console.error("Delete error:", err.message);
    res.status(500).json({ 
      error: "Server Error",
      details: err.message 
    });
  }
};

exports.allowTrainProfile = async (req, res) => {
  try {
    const { profileId } = req.params;

    // Validate profileId
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(profileId)) {
      return res.status(400).json({ error: 'Invalid profileId format' });
    }

    // Update profile to allow training
    await pool.query("UPDATE profiles SET trainable_profile = FALSE WHERE id = $1", [profileId]);
    
    res.json({ message: "Profile training enabled successfully" });
  } catch (err) {
    console.error("Enable training error:", err.message);
    res.status(500).json({ error: "Server Error", details: err.message });
  }
};