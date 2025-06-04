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
    const result = await pool.query("SELECT * FROM profiles ORDER BY id");
    res.json(result.rows);
  } catch (err) {
    console.error(err.message);
    res.status(500).send("Server Error");
  }
};

// exports.trainProfile = async (req, res) => {
//   const { id } = req.params;
//   try {
//     if (!req.file) return res.status(400).json({ error: "No file uploaded" });

//     // const fileData = {
//     //   name: req.file.filename,
//     //   type: req.file.mimetype,
//     //   size: req.file.size,
//     //   path: req.file.path,
//     // };

//     const fileData = {
//       filename: req.file.filename,
//       uploaded_at: new Date().toISOString()
//     };

//     const recentUpload = await pool.query(
//       "SELECT last_updated FROM profiles WHERE id = $1 AND last_updated > NOW() - INTERVAL '10 seconds'",
//       [id]
//     );
//     if (recentUpload.rows.length > 0)
//       return res.status(429).json({ error: "Duplicate upload detected, please wait" });

//     const pdfBuffer = await fs.readFile(req.file.path);
//     const pdfData = await pdfParse(pdfBuffer);
//     const pdfText = pdfData.text.trim();

//     const existing = await pool.query("SELECT content FROM profiles WHERE id = $1::uuid", [id]);
//     let newContent = pdfText;
//     if (existing.rows.length && existing.rows[0].content) {
//       newContent = existing.rows[0].content + "\n\n" + pdfText;
//     }

//     // const result = await pool.query(
//     //   `UPDATE profiles SET training_file = COALESCE(training_file, '[]'::jsonb) || $1::jsonb,
//     //   content = $2, last_updated = CURRENT_TIMESTAMP WHERE id = $3::uuid RETURNING *`,
//     //   [JSON.stringify([fileData]), newContent, id]
//     // );

//     const result = await pool.query(
//       `UPDATE profiles SET training_file = COALESCE(training_file, '[]'::jsonb) || $1::jsonb,
//        content = $2, last_updated = CURRENT_TIMESTAMP WHERE id = $3::uuid RETURNING *`,
//       [JSON.stringify([fileData]), newContent, id]
//     );

//     const pythonPath = path.join(__dirname, "..", ".venv", "Scripts", "python.exe");
//     const scriptPath = path.join(__dirname, "..", "vectorize_pdf.py");
//     const absoluteFilePath = path.resolve(req.file.path); // Converts to absolute
//     await exec(`"${pythonPath}" "${scriptPath}" "${absoluteFilePath}" "${id}"`);
    
//     // await exec(`"${pythonPath}" "${scriptPath}" "${req.file.path}" "${id}"`);

//     res.json(result.rows[0]);
//   } catch (err) {
//     console.error("Upload error:", err.message);
//     res.status(500).json({ error: "Upload failed", details: err.message });
//   }
// };

exports.trainProfile = async (req, res) => {
  console.log('Handling POST /train/:profileId:', req.params.profileId);
  try {
    const { profileId } = req.params;
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(profileId)) {
      console.warn(`Invalid profileId format: ${profileId}`);
      return res.status(400).json({ error: 'Invalid profileId format' });
    }
 
    const pdfFile = req.file;
    if (!pdfFile) {
      console.warn('PDF file missing in request');
      return res.status(400).json({ error: 'PDF file required' });
    }
 
    const filePath = path.join(__dirname, 'Uploads', `${profileId}_${pdfFile.originalname}`);
    await fs.rename(pdfFile.path, filePath);
    console.log(`Saved PDF to: ${filePath}`);
 
    const dataBuffer = await fs.readFile(filePath);
    const pdfData = await pdfParse(dataBuffer);
    const content = pdfData.text;
    console.log(`Extracted PDF content length: ${content.length} characters`);
 
    const tempContentFile = path.join(__dirname, 'temp', `${uuidv4()}.txt`);
    await fs.mkdir(path.dirname(tempContentFile), { recursive: true });
    await fs.writeFile(tempContentFile, content);
    console.log(`Saved content to temp file: ${tempContentFile}`);
 
    const trainingFileData = [{
      name: pdfFile.originalname,
      path: filePath,
      size: pdfFile.size,
      type: pdfFile.mimetype,
      processed: true
    }];
    await pool.query(
      'UPDATE profiles SET training_file = $1::jsonb WHERE id = $2',
      [JSON.stringify(trainingFileData), profileId]
    );
    console.log(`Updated profiles.training_file for profileId: ${profileId}`);
 
    const execPromise = util.promisify(exec);
    const command = `"${PYTHON_EXECUTABLE}" train_profile.py "${profileId}" "${tempContentFile}" "${pdfFile.originalname}"`;
    console.log(`Executing training command: ${command}`);
    const { stdout, stderr } = await execPromise(command, { maxBuffer: 1024 * 1024 });
    console.log(`Training stdout: ${stdout}`);
    if (stderr && (stderr.includes('Error:') || stderr.includes('Exception'))) {
      console.error('Training script failed:', stderr);
      throw new Error(`Training script failed: ${stderr}`);
    }
 
    await fs.unlink(tempContentFile).catch(err => console.warn(`Failed to delete temp file: ${tempContentFile}, ${err}`));
    console.log('Profile trained successfully');
    res.json({ message: 'Profile trained successfully' });
  } catch (err) {
    console.error('Training error:', err);
    res.status(500).json({ error: 'Training failed', details: err.message });
  }
}

exports.deleteProfile = async (req, res) => {
  try {
    const { id } = req.params;

    // 1. Fetch training_file info for the profile
    const profileRes = await pool.query("SELECT training_file FROM profiles WHERE id = $1::uuid", [id]);
    const trainingFiles = profileRes.rows[0]?.training_file || [];

    // 2. Delete associated files from disk
    for (const file of trainingFiles) {
      const filePath = path.join(__dirname, "..", "uploads", file.filename);
      try {
        await fs.unlink(filePath);
        console.log(`Deleted file: ${filePath}`);
      } catch (err) {
        console.warn(`Could not delete file: ${filePath}`, err.message); // File may not exist
      }
    }

    // 3. Delete profile from DB
    await pool.query("DELETE FROM profiles WHERE id = $1::uuid", [id]);
    const result = await pool.query("DELETE FROM job_profile WHERE profile_id = $1 RETURNING *", [id]);

    res.json({ message: "Profile and files deleted", deleted: result.rows });
  } catch (err) {
    console.error("Delete error:", err.message);
    res.status(500).send("Server Error");
  }
};
