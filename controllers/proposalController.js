const db = require('../db');

exports.getProposalById = async (req, res) => {
    const { profile_id } = req.params;
    try {
        // Fetch all proposal feedback and related data for the profile
        const result = await db.query(`
                                        SELECT * 
                                        FROM proposal_feedback 
                                        WHERE profile_id = $1 
                                            AND score >= 80
                                        `, [profile_id]);

        if (result.rows.length === 0) {
            return res.status(404).json({
                status: 404,
                message: 'No proposal feedback found for this profile',
                data: []
            });
        }
        console.log('Fetched proposal feedback:', result.rows);

        res.status(200).json({
            status: 200,
            message: 'Proposal feedback retrieved successfully',
            data: result.rows
        });
    } catch (error) {
        console.error('Error fetching proposal feedback:', error);
        res.status(500).json({
            status: 500,
            message: 'Error fetching proposal feedback',
            error: error.message
        });
    }
};


exports.deleteProposal = async (req, res) => {
    const { id } = req.params;

    try {
        // Delete proposal feedback by ID
        const result = await db.query(`
            DELETE FROM proposal_feedback 
            WHERE id = $1 
            RETURNING *
        `, [id]);

        if (result.rows.length === 0) {
            return res.status(404).json({
                status: 404,
                message: 'Proposal feedback not found'
            });
        }

        res.status(200).json({
            status: 200,
            message: 'Proposal feedback deleted successfully',
            data: result.rows[0]
        });
    } catch (error) {
        console.error('Error deleting proposal feedback:', error);
        res.status(500).json({
            status: 500,
            message: 'Error deleting proposal feedback',
            error: error.message
        });
    }
};

// exports.getProposalById = getProposalById;