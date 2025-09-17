# Upwork GraphQL API Job Search Filters Table

This table lists all filters for the `marketplaceJobPostingsSearch` query's `MarketplaceJobPostingsSearchFilter` input type, as per Upwork's official GraphQL API documentation. Use these in the `marketPlaceJobFilter` object to fetch relevant jobs. Examples are formatted for JavaScript `variables` in a GraphQL request.

| Filter Name | What It Does (Simple) | Type | Example Value to Pass | Notes and Tips |
|-------------|-----------------------|------|-----------------------|----------------|
| `titleExpression_eq` | Filters jobs by title keywords (supports OR/AND/NOT) | String | `"titleExpression_eq": "frontend OR web developer"` | Use for specific roles (e.g., "developer"). Test expressions like `"React -junior"` to exclude terms. Great for reducing irrelevant jobs. |
| `skillExpression_eq` | Filters by required skills (basic OR/AND logic) | String | `"skillExpression_eq": "Python JavaScript"` | Use skill names from `searchSkills` query. Spaces mean AND; "OR" for alternatives. For complex OR, run multiple queries or filter after. |
| `searchTerm_eq` | Searches title, description, and skills broadly | String | `"searchTerm_eq": "data analysis"` | Broadens results; use with other filters to narrow. Supports `"term1 term2"` (AND) or `"term1 OR term2"`. |
| `category_eq` | Filters by job category (e.g., Development) | String (ID or name) | `"category_eq": "development"` | Get valid IDs from `searchCategories` query (e.g., `searchCategories(searchTerm: "IT") { edges { node { id name } } }`). Avoids non-relevant fields. |
| `budgetMin_gte` | Minimum budget for fixed-price or hourly jobs | Float (USD) | `"budgetMin_gte": 500` | Cuts out low-pay jobs. Needs "Read Job Details" scope. Use with `paymentType_eq`. |
| `budgetMax_lte` | Maximum budget for fixed-price or hourly jobs | Float (USD) | `"budgetMax_lte": 2000` | Caps high-budget jobs. Combine with `budgetMin_gte` for range. Requires same scope. |
| `hourlyRateMin_gte` | Minimum hourly rate | Float (USD) | `"hourlyRateMin_gte": 20` | For hourly jobs only. Use instead of `budgetMin_gte` if filtering hourly. Needs scope. |
| `hourlyRateMax_lte` | Maximum hourly rate | Float (USD) | `"hourlyRateMax_lte": 100` | Caps hourly rates. Pair with `hourlyRateMin_gte`. Same scope as budget. |
| `paymentType_eq` | Job payment type (fixed or hourly) | String/Enum: `"FIXED"`, `"HOURLY"` | `"paymentType_eq": "FIXED"` | Pick your preferred payment model. Useful to focus on stable gigs. |
| `experienceLevel_eq` | Experience level required | String/Enum: `"ENTRY_LEVEL"`, `"INTERMEDIATE"`, `"EXPERT"` | `"experienceLevel_eq": "INTERMEDIATE"` | Matches your skill level. Avoids over/under-qualified jobs. |
| `projectLength_eq` | How long the job lasts | String/Enum: `"HOURS"`, `"WEEKS"`, `"MONTHS"`, `"MORE_THAN_6_MONTHS"` | `"projectLength_eq": "MONTHS"` | Filters for short or long-term work. Good for commitment planning. |
| `clientHires_eq` | Exact number of client’s past hires | Int | `"clientHires_eq": 0` | Targets new clients (0 hires) or specific hire counts. Use for niche strategies. |
| `clientHires_gt` | Minimum number of client’s past hires | Int | `"clientHires_gt": 5` | Ensures experienced clients (reliable hirers). Reduces risk of bad clients. |
| `clientHires_lt` | Maximum number of client’s past hires | Int | `"clientHires_lt": 10` | Caps client experience (e.g., avoid huge firms). Less common but strategic. |
| `postedOn_gt` | Jobs posted after a date | String (ISO datetime) | `"postedOn_gt": "2025-09-12T00:00:00Z"` | Your 6-min window works (`new Date(Date.now() - 6*60*1000).toISOString()`). Widen to 1 day for more. |
| `postedOn_lt` | Jobs posted before a date | String (ISO datetime) | `"postedOn_lt": "2025-09-13T00:00:00Z"` | Rarely used; pairs with `postedOn_gt` for time ranges. |
| `postedOn_gte` | Jobs posted on or after a date | String (ISO datetime) | `"postedOn_gte": "2025-09-12T00:00:00Z"` | Like `postedOn_gt` but includes the exact time. Use for precision. |
| `postedOn_lte` | Jobs posted on or before a date | String (ISO datetime) | `"postedOn_lte": "2025-09-13T00:00:00Z"` | Complements `postedOn_gte` for ranges. Less common. |
| `daysPosted_eq` | Exact days since job posted | Int | `"daysPosted_eq": 0` | Your code uses this (today’s jobs). Set to 1-3 for recent but active postings. |
| `daysPosted_gt` | More than X days since posted | Int | `"daysPosted_gt": 1` | Grabs older but still open jobs. Combine with recency sort. |
| `daysPosted_lt` | Less than X days since posted | Int | `"daysPosted_lt": 7` | Limits to fresh jobs (e.g., <7 days). Alternative to `postedOn`. |
| `jobPostingAccess_eq` | Job visibility (public or invite-only) | String/Enum: `"PUBLIC_INDEX"`, `"INVITE_ONLY"` | `"jobPostingAccess_eq": "PUBLIC_INDEX"` | Keep for public jobs (like your code). `"INVITE_ONLY"` needs specific access. |
| `sinceId_eq` | Start from a specific job ID/cursor | String | `"sinceId_eq": "job12345"` | For resuming searches or pagination. Use with `pagination: { after: "cursor" }`. Not a content filter. |

## Notes for Using Filters
- **Source**: Compiled from Upwork GraphQL API docs (https://www.upwork.com/developer/documentation/graphql/api/docs/index.html), schema in GraphQL Explorer, and community posts (Stack Overflow, Upwork Community, 2023-2025).
- **Permissions**: Add "Read marketplace Job Postings - Public" scope in Upwork API settings (GraphQL tab). For budget/hourly rate, request "Read Job Details" scope or you’ll get 403 errors.
- **Dependencies**: For `category_eq` or `skillExpression_eq`, query `searchCategories` or `searchSkills` first (e.g., `searchSkills(searchTerm: "web") { edges { node { id name } } }`) to get valid IDs/names.
- **Expressions**: In `titleExpression_eq` or `skillExpression_eq`, use `"term1 term2"` (AND), `"term1 OR term2"` (OR), `"-term"` (NOT, limited support). Complex OR (e.g., multiple skills) may need multiple queries or post-fetch filtering.
- **Pagination**: Set `pagination: { first: 100, after: null }` to max out results (100/page). Loop with `after: pageInfo.endCursor` if `pageInfo.hasNextPage` is true.
- **Sorting**: Use `sortAttributes: [{ field: "RECENCY" }]` for newest jobs or `"RELEVANCY"` for best matches. Field options: `"RECENCY"`, `"RELEVANCY"`, `"BUDGET"`, `"CREATE_TIME"`.
- **Search Type**: Set `searchType: "USER_JOBS_SEARCH"` for personalized results or `"JOBS_FEED"` for public. Affects relevance slightly.
- **Testing**: Use Upwork’s GraphQL Explorer to validate filters. If no results, loosen one filter (e.g., remove `budgetMin_gte`) or check `response.data.errors`.
- **Rate Limits**: ~1000 calls/day. Fetch 100 jobs per call to stay efficient.
- **No Missing Filters**: This is the complete documented set. Undocumented fields (e.g., geo-location) don’t exist in GraphQL; use post-fetch filtering on `client.country` if needed.

## Example Usage in Code
Add to your `variables` object in the `fetchLatestJobs` function:
```javascript
const variables = {
  marketPlaceJobFilter: {
    jobPostingAccess: "PUBLIC_INDEX",
    daysPosted_eq: 0,
    postedOn_gt: new Date(Date.now() - 6 * 60 * 1000).toISOString(),
    skillExpression_eq: "React JavaScript",
    budgetMin_gte: 500,
    paymentType_eq: "FIXED",
    category_eq: "development",
    experienceLevel_eq: "INTERMEDIATE",
    clientHires_gt: 1
  },
  searchType: "USER_JOBS_SEARCH",
  sortAttributes: [{ field: "RECENCY" }],
  pagination: { first: 50, after: null }
};
```

## How to Download
Copy this Markdown content into a `.md` file or convert to CSV/HTML for your needs. Test filters in GraphQL Explorer to customize for your use case (e.g., specific skills or budget).