# Upwork Platform (Backend)

Contains all Upwork-specific backend code:
- fetcher.js: incremental fetch + filtering + scoring
- tokenManager.js: OAuth refresh
- auth.js: one-off token exchange utilities
- routes/upworkJobsRoutes.js and controllers/upworkJobsController.js: Upwork jobs API

To add a new platform, create a sibling folder and export it via platforms/index.js.


