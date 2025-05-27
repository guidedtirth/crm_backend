const pool = require("../db");
const pdfParse = require("pdf-parse");
const path = require("path");
const fs = require("fs").promises;
const util = require("util");
const exec = util.promisify(require("child_process").exec);

exports.createProfile = async (req, res) => {
  try {
    const { name } = req.body;
    const result = await pool.query("INSERT INTO profiles (name) VALUES ($1) RETURNING *", [name]);
    const profileId = result.rows[0].id;

    await pool.query("INSERT INTO job_profile (profile_id) VALUES ($1)", [profileId]);

    res.json(result.rows[0]);
  } catch (err) {
    console.error(err.message);
    res.status(500).send("Server Error");
  }
};

exports.getProfiles = async (_req, res) => {
  try {
    const result = await pool.query("SELECT * FROM profiles ORDER BY id");
    res.json(result.rows);
  } catch (err) {
    console.error(err.message);
    res.status(500).send("Server Error");
  }
};

exports.trainProfile = async (req, res) => {
  const { id } = req.params;
  try {
    if (!req.file) return res.status(400).json({ error: "No file uploaded" });

    const fileData = {
      name: req.file.filename,
      type: req.file.mimetype,
      size: req.file.size,
      path: req.file.path,
    };

    const recentUpload = await pool.query(
      "SELECT last_updated FROM profiles WHERE id = $1 AND last_updated > NOW() - INTERVAL '10 seconds'",
      [id]
    );
    if (recentUpload.rows.length > 0)
      return res.status(429).json({ error: "Duplicate upload detected, please wait" });

    const pdfBuffer = await fs.readFile(req.file.path);
    const pdfData = await pdfParse(pdfBuffer);
    const pdfText = pdfData.text.trim();

    const existing = await pool.query("SELECT content FROM profiles WHERE id = $1::uuid", [id]);
    let newContent = pdfText;
    if (existing.rows.length && existing.rows[0].content) {
      newContent = existing.rows[0].content + "\n\n" + pdfText;
    }

    const result = await pool.query(
      `UPDATE profiles SET training_file = COALESCE(training_file, '[]'::jsonb) || $1::jsonb,
      content = $2, last_updated = CURRENT_TIMESTAMP WHERE id = $3::uuid RETURNING *`,
      [JSON.stringify([fileData]), newContent, id]
    );

    const pythonPath = path.join(__dirname, "..", "venv", "Scripts", "python.exe");
    const scriptPath = path.join(__dirname, "..", "vectorize_pdf.py");
    await exec(`"${pythonPath}" "${scriptPath}" "${req.file.path}" "${id}"`);

    res.json(result.rows[0]);
  } catch (err) {
    console.error("Upload error:", err.message);
    res.status(500).json({ error: "Upload failed", details: err.message });
  }
};

exports.deleteProfile = async (req, res) => {
  try {
    const { id } = req.params;
    await pool.query("DELETE FROM profiles WHERE id = $1::uuid", [id]);
    const result = await pool.query("DELETE FROM job_profile WHERE profile_id = $1 RETURNING *", [id]);
    res.json({ message: "Profile deleted", deleted: result.rows });
  } catch (err) {
    console.error(err.message);
    res.status(500).send("Server Error");
  }
};
