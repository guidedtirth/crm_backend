#!/usr/bin/env node
const axios = require("axios");
const path = require("path");
const dotenv = require("dotenv");

dotenv.config({ path: path.resolve(__dirname, ".env") });

const ACCESS_TOKEN = process.env.ACCESS_TOKEN;
const TENANT_ID = process.env.UPWORK_TENANT_ID || "";
const ENDPOINT = "https://api.upwork.com/graphql";

if (!ACCESS_TOKEN) {
  console.error("❌ Missing ACCESS_TOKEN in .env");
  process.exit(1);
}

function headers() {
  const h = {
    Authorization: `Bearer ${ACCESS_TOKEN}`,
    "Content-Type": "application/json",
  };
  if (TENANT_ID) h["X-Upwork-API-TenantId"] = TENANT_ID;
  return h;
}

/* ----------------------------- CLI parameters ----------------------------- */
function getArg(name) {
  const pref = `--${name}=`;
  const a = process.argv.find((x) => x.startsWith(pref));
  return a ? a.slice(pref.length) : undefined;
}
const catIdsArg = getArg("catIds");               // e.g., "123,456"
const minHourly = Number(getArg("minHourly") || 15);
const minBudget = Number(getArg("minBudget") || 5000);
const maxProps  = Number(getArg("maxProposals") || 50);

const categoryIds = (catIdsArg || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean)
  .map((n) => Number(n))
  .filter((n) => Number.isFinite(n));

/* --------------------------- Enum literal helper -------------------------- */
// Wrap enum values so the serializer outputs them UNQUOTED.
const enumVal = (name) => ({ __enum: String(name) });

/* ------------------------ GraphQL literal serializer ---------------------- */
function toGraphQLInputLiteral(value) {
  if (value === null) return "null";
  if (value && typeof value === "object" && "__enum" in value) {
    // Output enums without quotes
    return value.__enum;
  }
  const t = typeof value;
  if (t === "number" || t === "boolean") return String(value);
  if (t === "string") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(toGraphQLInputLiteral).join(", ") + "]";
  if (t === "object") {
    return "{ " + Object.entries(value).map(([k, v]) => `${k}: ${toGraphQLInputLiteral(v)}`).join(", ") + " }";
  }
  return "null";
}

/* ------------------------- Introspection: IntRange ------------------------ */
async function introspectIntRange() {
  const q = `
    query {
      __type(name: "IntRange") {
        inputFields { name }
      }
    }
  `;
  const resp = await axios.post(ENDPOINT, { query: q }, { headers: headers(), timeout: 20000 });
  const errs = resp.data?.errors;
  if (errs?.length) throw new Error(JSON.stringify(errs));
  const names = (resp.data?.data?.__type?.inputFields || []).map(f => f.name);
  const pairs = [
    ["min", "max"],
    ["from", "to"],
    ["low", "high"],
    ["start", "end"],
  ];
  for (const [a, b] of pairs) if (names.includes(a) && names.includes(b)) return { lowKey: a, highKey: b };
  if (names.length >= 2) return { lowKey: names[0], highKey: names[1] };
  throw new Error("Could not determine IntRange field names");
}

/* ---------------------------------- Main --------------------------------- */
(async function main() {
  try {
    const { lowKey, highKey } = await introspectIntRange();

    // Build filter using YOUR IntRange key names and proper enums
    const filter = {
      ...(categoryIds.length ? { categoryIds_any: categoryIds } : {}),
      jobType_eq: enumVal("HOURLY"),
      workload_eq: enumVal("FULL_TIME"), // ≈ 30+ hrs/week
      verifiedPaymentOnly_eq: true,
      clientHiresRange_eq: { [lowKey]: 1, [highKey]: 100000 },   // ≥1 hire
      hourlyRate_eq:       { [lowKey]: minHourly, [highKey]: 1000 },     // ≥ $15/hr (default)
      budgetRange_eq:      { [lowKey]: minBudget, [highKey]: 10000000 }, // ≥ $5000
      proposalRange_eq:    { [lowKey]: 0, [highKey]: maxProps },         // ≤ 50
    };

    const filterLiteral = toGraphQLInputLiteral(filter);

    const SELECTION = `
      totalCount
      edges {
        node {
          id
          title
          createdDateTime
          amount { currency rawValue }
          category
          skills { name }
          client { location { country } }
        }
      }
      pageInfo { hasNextPage endCursor }
    `;

    // Inline the filter (no variable for filter) so Map-scalar tenants are happy
    const query = `
      query ($searchType: MarketplaceJobPostingSearchType, $sortAttributes: [MarketplaceJobPostingSearchSortAttribute]) {
        marketplaceJobPostingsSearch(
          marketPlaceJobFilter: ${filterLiteral}
          searchType: $searchType
          sortAttributes: $sortAttributes
        ) { ${SELECTION} }
      }
    `;

    const variables = {
      searchType: "USER_JOBS_SEARCH",
      sortAttributes: [{ field: "RECENCY" }],
    };

    console.log("🔧 Using filter:", filter);
    const resp = await axios.post(ENDPOINT, { query, variables }, { headers: headers(), timeout: 30000 });
    const { data, errors } = resp.data || {};
    if (errors?.length) {
      console.error("❌ GraphQL errors:", JSON.stringify(errors, null, 2));
      process.exit(1);
    }

    const payload = data?.marketplaceJobPostingsSearch;
    const edges = payload?.edges || [];
    console.log(`\n✅ Returned (this page): ${edges.length} | Reported total: ${payload?.totalCount ?? "unknown"}`);
    for (const { node } of edges) {
      const budget = node.amount ? `${node.amount.currency} ${node.amount.rawValue}` : "";
      console.log(`- ${node.title} | ${node.category || ""} | ${budget} | ${node.client?.location?.country || ""}`);
    }
    if (payload?.pageInfo?.hasNextPage) {
      console.log("\nℹ️ There are more results (hasNextPage = true). Add pagination if needed.");
    }
  } catch (err) {
    console.error("\n❌ Failed:", err.message);
    if (err.response?.data) console.error("Server response:", JSON.stringify(err.response.data, null, 2));
    process.exit(1);
  }
})();
