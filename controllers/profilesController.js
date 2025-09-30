/**
 * Profiles Controller
 * Create/list/delete profiles and manage training flags/files.
 */
const pool = require("../db");
const pdfParse = require("pdf-parse");
const path = require("path");
const fs = require("fs").promises;
const util = require("util");
const exec = util.promisify(require("child_process").exec);

/** Create a profile under the authenticated company */
exports.createProfile = async (req, res) => {
  try {
    console.log("Creating profile with data:", req.body);
    const { name } = req.body;
    const companyId = req.user?.company_id;
    if (!companyId) return res.status(401).json({ error: 'Missing company scope' });
    const result = await pool.query("INSERT INTO profiles (name, company_id, trainable_profile) VALUES ($1, $2, FALSE) RETURNING *", [name, companyId]);

    res.json(result.rows[0]);
  } catch (err) {
    console.error(err.message);
    res.status(500).send("Server Error");
  }
};

/** List profiles for the authenticated company */
exports.getProfiles = async (req, res) => {
  try {
    const companyId = req.user?.company_id;
    if (!companyId) return res.status(401).json({ error: 'Missing company scope' });
    const result = await pool.query("SELECT * FROM profiles WHERE company_id = $1 ORDER BY last_updated DESC", [companyId]);
    res.json(result.rows);
  } catch (err) {
    console.error(err.message);
    res.status(500).send("Server Error");
  }
};


/** Delete a profile and any associated training files from disk */
exports.deleteProfile = async (req, res) => {
  try {
    const { id } = req.params;

    // 1. Fetch training_file info for the profile
    const companyId = req.user?.company_id;
    if (!companyId) return res.status(401).json({ error: 'Missing company scope' });
    const profileRes = await pool.query("SELECT training_file FROM profiles WHERE id = $1::uuid AND company_id = $2", [id, companyId]);
    
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
    await pool.query("DELETE FROM profiles WHERE id = $1::uuid AND company_id = $2", [id, companyId]);

    res.json({ 
      message: "Profile and files deleted successfully",
      deletedProfileId: id,
      deletedFiles: trainingFiles.map(f => f.name)
    });
  } catch (err) {
    console.error("Delete error:", err.message);
    res.status(500).json({ 
      error: "Server Error",
      details: err.message 
    });
  }
};

/** Enable/disable profile training flag (currently sets trainable_profile = FALSE) */
exports.allowTrainProfile = async (req, res) => {
  try {
    const { profileId } = req.params;

    // Validate profileId
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(profileId)) {
      return res.status(400).json({ error: 'Invalid profileId format' });
    }

    const companyId = req.user?.company_id;
    if (!companyId) return res.status(401).json({ error: 'Missing company scope' });
    // Update profile to disallow training
    await pool.query("UPDATE profiles SET trainable_profile = FALSE WHERE id = $1 AND company_id = $2", [profileId, companyId]);
    
    res.json({ message: "Profile training enabled successfully" });
  } catch (err) {
    console.error("Enable training error:", err.message);
    res.status(500).json({ error: "Server Error", details: err.message });
  }
};

/** Explicitly enable training for a profile (opt-in) */
exports.enableTrainProfile = async (req, res) => {
  try {
    const { profileId } = req.params;

    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(profileId)) {
      return res.status(400).json({ error: 'Invalid profileId format' });
    }

    const companyId = req.user?.company_id;
    if (!companyId) return res.status(401).json({ error: 'Missing company scope' });

    await pool.query("UPDATE profiles SET trainable_profile = TRUE WHERE id = $1 AND company_id = $2", [profileId, companyId]);

    res.json({ message: "Profile training enabled" });
  } catch (err) {
    console.error("Enable training error:", err.message);
    res.status(500).json({ error: "Server Error", details: err.message });
  }
};