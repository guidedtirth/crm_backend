// Upwork utilities: canonicalization and summarization of job nodes

/**
 * Produce a consistent, flattened job object for storage and downstream use.
 * - Ensures top-level title/description
 * - Lifts attachments and contractTerms from nested job
 * - Keeps commonly used fields (amount, client, skills, occupations, etc.)
 * - Removes nested job subtree to avoid duplication/ambiguity
 */
function canonicalizeJobNode(node) {
  if (!node || typeof node !== 'object') return {};
  const j = node.job || {};
  const title = node.title || (j.content && j.content.title) || '';
  const description = node.description || (j.content && j.content.description) || '';
  const attachments = Array.isArray(j.attachments) ? j.attachments : [];
  const contractTerms = j.contractTerms || null;

  return {
    // identifiers and meta
    id: node.id || j.id || null,
    recordNumber: node.recordNumber ?? null,
    createdDateTime: node.createdDateTime ?? null,
    publishedDateTime: node.publishedDateTime ?? null,
    renewedDateTime: node.renewedDateTime ?? null,

    // content
    title,
    description,
    attachments,
    contractTerms,

    // commercial
    amount: node.amount || null,
    hourlyBudgetType: node.hourlyBudgetType || null,
    hourlyBudgetMin: node.hourlyBudgetMin || null,
    hourlyBudgetMax: node.hourlyBudgetMax || null,
    weeklyBudget: node.weeklyBudget || null,

    // client and location
    client: node.client || null,

    // classification
    category: node.category || null,
    subcategory: node.subcategory || null,
    occupations: node.occupations || null,

    // misc
    duration: node.duration || null,
    durationLabel: node.durationLabel || null,
    engagement: node.engagement || null,
    engagementDuration: node.engagementDuration || null,
    totalApplicants: node.totalApplicants ?? null,
    preferredFreelancerLocation: node.preferredFreelancerLocation || null,
    preferredFreelancerLocationMandatory: node.preferredFreelancerLocationMandatory || false,
    premium: node.premium || false,
    clientNotSureFields: node.clientNotSureFields || null,
    clientPrivateFields: node.clientPrivateFields || null,
    applied: node.applied || false,
    enterprise: node.enterprise || false,
    experienceLevel: node.experienceLevel || null,
    relevance: node.relevance || null,
    relevanceEncoded: node.relevanceEncoded || null,
    localJobUserDistance: node.localJobUserDistance || null,
    totalFreelancersToHire: node.totalFreelancersToHire || null,
    teamId: node.teamId || null,
    freelancerClientRelation: node.freelancerClientRelation || null,

    // skills
    skills: Array.isArray(node.skills) ? node.skills : [],
  };
}

/**
 * Build a compact JSON summary for prompting (token-efficient).
 */
function summarizeJobForPrompt(node) {
  const title = node?.title || '';
  const description = String(node?.description || '').replace(/\s+/g, ' ').slice(0, 700);
  const skills = Array.isArray(node?.skills)
    ? node.skills.map(s => s?.name || s?.prettyName || '').filter(Boolean).slice(0, 8)
    : [];
  const budget = {
    hourlyMin: node?.hourlyBudgetMin?.rawValue || null,
    hourlyMax: node?.hourlyBudgetMax?.rawValue || null,
    amount: node?.amount?.rawValue || null,
    currency: node?.amount?.currency || null,
  };
  const location = {
    country: node?.client?.location?.country || null,
    city: node?.client?.location?.city || null,
  };
  const category = {
    id: node?.occupations?.category?.id || node?.category || null,
    label: node?.occupations?.category?.prefLabel || null,
    subcategory: node?.subcategory || null,
  };
  return {
    id: node?.id || null,
    title,
    description,
    skills,
    experienceLevel: node?.experienceLevel || null,
    budget,
    location,
    category,
    duration: node?.durationLabel || null,
    applicants: node?.totalApplicants ?? null,
    engagementWeeks: node?.engagementDuration?.weeks ?? null,
  };
}

module.exports = { canonicalizeJobNode, summarizeJobForPrompt };


