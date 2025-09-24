/**
 * upworkServices.js
 *
 * Simple Upwork Rooms and Messages Helper
 *  - list: List all rooms
 *  - conversations: Get all messages for a single room (now with images/files)
 *  - all_conversations: List all rooms and get all messages for each
 *  - send: Send a message to a room (text + optional attachments)
 *  - introspect: Get schema info for types like RoomFilter
 *
 * Setup:
 *   1. Install Node.js[](https://nodejs.org)
 *   2. Run: npm install axios
 *   3. Save this file as upworkServices.js
 *   4. Get token from Upwork developer dashboard with scopes: read_rooms, read_stories, write_stories
 *
 * Run in PowerShell:
 *   $env:ACCESS_TOKEN = "your_token"
 *   cd "D:\New folder\marcketing backend\marketing_backend"
 *   node upworkServices.js list
 *   node upworkServices.js conversations --roomId "room_id"
 *   node upworkServices.js all_conversations
 *   node upworkServices.js send --roomId "room_id" --text "Hi!" [--attachmentId "file_id"]
 *   node upworkServices.js introspect RoomStory
 */

const axios = require('axios');

const ENDPOINT = 'https://api.upwork.com/graphql';
const ACCESS_TOKEN = process.env.ACCESS_TOKEN || 'oauth2v2_107006e8e49a6de6913c4c38c6895d5d';
const TENANT_ID = process.env.UPWORK_TENANT_ID || '';

if (!ACCESS_TOKEN) {
  console.error('Set $env:ACCESS_TOKEN = "your_token" in PowerShell');
  process.exit(1);
}

function headers() {
  const h = {
    Authorization: `Bearer ${ACCESS_TOKEN}`,
    'Content-Type': 'application/json',
  };
  if (TENANT_ID) h['X-Upwork-API-TenantId'] = TENANT_ID;
  return h;
}

function isValidationError(err) {
  return /ValidationError/i.test(err?.message || err);
}

async function gql(query, variables) {
  try {
    const res = await axios.post(ENDPOINT, { query, variables }, { headers: headers(), timeout: 20000 });
    const errs = res.data?.errors || [];
    if (errs.length) {
      console.error('Errors:', JSON.stringify(errs, null, 2));
      throw new Error(JSON.stringify(errs, null, 2));
    }
    return res.data?.data;
  } catch (e) {
    console.error('Error:', e?.response?.data || e.message);
    throw e;
  }
}

/* ---------------- Introspect Type ---------------- */

async function introspectType(typeName) {
  const query = `
    query($typeName: String!) {
      __type(name: $typeName) {
        name
        inputFields { name type { name ofType { name } } }
        fields { name type { name ofType { name } } }
      }
    }`;
  try {
    const data = await gql(query, { typeName });
    console.log(JSON.stringify(data, null, 2));
  } catch (e) {
    console.error(`Introspection failed. Run with valid token and check scopes.`);
    throw e;
  }
}

/* ---------------- List Rooms ---------------- */

async function listRooms({ filter = null, sortOrder = 'DESC', first = 100 }) {
  const query = `
    query($filter: RoomFilter, $sortOrder: SortOrder, $first: Int!, $after: String) {
      roomList(filter: $filter, sortOrder: $sortOrder, pagination: { first: $first, after: $after }) {
        edges { node { id roomName latestStory { createdDateTime } } }
        pageInfo { hasNextPage endCursor }
      }
    }`;
  let allEdges = [];
  let after = null;

  while (true) {
    try {
      const data = await gql(query, { filter, sortOrder, first, after });
      const conn = data?.roomList;
      if (conn) {
        allEdges = allEdges.concat(conn.edges || []);
        if (!conn.pageInfo?.hasNextPage) break;
        after = conn.pageInfo.endCursor;
      } else {
        break;
      }
    } catch (e) {
      if (isValidationError(e)) {
        console.warn('Query validation failed. Run "node upworkServices.js introspect RoomFilter" for valid fields or check schema.');
        return { edges: [], pageInfo: { hasNextPage: false, endCursor: null } };
      }
      throw e;
    }
  }
  if (!allEdges.length) {
    console.warn('No rooms found. Check token (read_rooms scope) or try --filter \'{"organizationRid_eq": "your_org_id"}\'.');
  }
  return { edges: allEdges, pageInfo: { hasNextPage: false, endCursor: null } };
}

/* ---------------- Get Messages for Room ---------------- */
async function listMessages({ roomId, filter = null }) {
    if (!roomId) throw new Error('Missing --roomId');
    const storyFilter = { ...filter, roomId_eq: roomId };
    const query = `
      query($filter: RoomStoryFilter!) {
        roomStories(filter: $filter) {
          edges { node { 
            id 
            message 
            createdDateTime 
            user { name id } 
            attachments { 
              objectReferenceId 
              objectType 
              metadata { key value } 
              createdDateTime 
              author { user { name id } } 
            } 
          } }
        }
      }`;
    try {
      const data = await gql(query, { filter: storyFilter });
      const conn = data?.roomStories;
      if (conn) {
        // Filter out edges with null user
        const validEdges = conn.edges.filter(edge => edge?.node?.user).map(edge => ({ ...edge }));
        console.warn(`Fetched ${validEdges.length} stories for room ${roomId}. Note: Upwork API limits to ~100 messages per query. Contact support[](https://support.upwork.com/hc/en-us/requests/new) for full access.`);
        return { edges: validEdges, pageInfo: { hasNextPage: false, endCursor: null } };
      }
      console.warn(`No stories for room ${roomId}. Check roomId or token (read_stories scope).`);
      return { edges: [], pageInfo: { hasNextPage: false, endCursor: null } };
    } catch (e) {
      if (isValidationError(e)) {
        console.warn(`Invalid fields or filter for room ${roomId}. Skipping. Error: ${e.message}`);
        return { edges: [], pageInfo: { hasNextPage: false, endCursor: null } };
      }
      throw e;
    }
  }

/* ---------------- Get Freelancer Profile ---------------- */
async function getFreelancerProfile() {
    const query = `
      query user {
        user {
          id
          email
          name
          photoUrl
          freelancerProfile {
            fullName
            firstName
            lastName
            availability {
              id
              capacity
              availabilityDateTime
              name
              createdDateTime
            }
            employmentRecords {
              id
              companyName
              jobTitle
              startDate
              endDate
              description
            }
            aggregates {
              jobSuccessScore
              totalHourlyJobs
              totalFixedJobs
            }
            portrait {
              portrait
            }
            profileCompletenessSummary {
              actual
              display
            }
          }
        }
      }`;
    try {
      const data = await gql(query, {});
      const profile = data?.user?.freelancerProfile;
      if (profile) {
        console.log('Freelancer profile fetched successfully!');
        return profile;
      }
      console.warn('No profile data found. Check token scopes (read_profile) or run "node upworkServices.js introspect FreelancerProfile" for valid fields.');
      return null;
    } catch (e) {
      if (isValidationError(e) || e.extensions?.classification === "ExecutionAborted") {
        console.warn('Invalid query or insufficient permissions. Ensure the ACCESS_TOKEN has scopes like read_profile_extended. Run "node upworkServices.js introspect FreelancerProfile" for valid fields.');
      }
      throw new Error(`Fetch failed: ${e.message}`);
    }
  }
  
  /* ---------------- Update Freelancer Availability ---------------- */
  async function updateFreelancerAvailability({ availability }) {
    if (!availability) throw new Error('Missing --availability (e.g., "AVAILABLE" or "NOT_AVAILABLE")');
    const query = `
      mutation($input: FreelancerProfileAvailabilityInput!) {
        updateFreelancerAvailability(input: $input) {
          id
          availability
          updatedDateTime
        }
      }`;
    const input = { availability };
    const variables = { input };
    try {
      const data = await gql(query, variables);
      const result = data?.updateFreelancerAvailability;
      if (result) {
        console.log('Freelancer availability updated successfully!');
        return result;
      }
      throw new Error('No result returned');
    } catch (e) {
      if (isValidationError(e)) {
        console.warn('Invalid mutation or input type. Check introspection output for updateFreelancerAvailability.');
      }
      throw new Error(`Update failed: ${e.message}`);
    }
  }
  
  /* ---------------- Get All Conversations ---------------- */
  
  async function allConversations({ filter = null }) {
    const rooms = await listRooms({ filter });
    const allData = {};
    for (const edge of rooms.edges || []) {
      const room = edge.node;
      console.log(`Fetching messages for ${room.roomName} (${room.id})...`);
      try {
        const messages = await listMessages({ roomId: room.id, filter });
        allData[room.id] = {
          roomName: room.roomName,
          latestStory: room.latestStory,
          messages: messages.edges || []
        };
      } catch (e) {
        console.error(`Failed to fetch messages for ${room.id} (${room.roomName}): ${e.message}. Skipping room.`);
      }
    }
    if (!Object.keys(allData).length) {
      console.warn('No conversations fetched. Check rooms or token scopes.');
    }
    return allData;
  }

/* ---------------- Send Message ---------------- */

async function sendMessage({ roomId, text, attachmentId = null }) {
  if (!roomId) throw new Error('Missing --roomId');
  if (!text) throw new Error('Missing --text');
  const query = `
    mutation($input: RoomStoryCreateInputV2!) {
      createRoomStoryV2(input: $input) {
        id
        message
        createdDateTime
        user { name id }
        attachments { id url type }
      }
    }`;
  const input = { roomId, message: text };
  if (attachmentId) input.attachmentId = attachmentId; // If attachments supported; check introspection
  const variables = { input };
  try {
    const data = await gql(query, variables);
    const story = data?.createRoomStoryV2;
    if (story) {
      console.log(`Message sent to ${roomId}!`);
      return story;
    }
    throw new Error('No story returned');
  } catch (e) {
    if (isValidationError(e)) {
      console.warn('Invalid mutation or input type. Check introspection output.');
    }
    throw new Error(`Send failed: ${e.message}`);
  }
}

/* ---------------- CLI ---------------- */

function parseFlags(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const val = argv[i + 1];
      if (val && !val.startsWith('--')) { out[key] = val; i++; }
      else out[key] = true;
    }
  }
  if (out.filter) out.filter = JSON.parse(out.filter || '{}');
  return out;
}

async function main() {
    const [cmd, ...rest] = process.argv.slice(2);
    const flags = parseFlags(rest);
  
    try {
      if (cmd === 'list') {
        const rooms = await listRooms(flags);
        console.log(JSON.stringify(rooms, null, 2));
      } else if (cmd === 'conversations') {
        const messages = await listMessages(flags);
        console.log(JSON.stringify(messages, null, 2));
      } else if (cmd === 'all_conversations') {
        const data = await allConversations(flags);
        console.log(JSON.stringify(data, null, 2));
      } else if (cmd === 'send') {
        const story = await sendMessage(flags);
        console.log(JSON.stringify(story, null, 2));
      } else if (cmd === 'get_profile') {
        const profile = await getFreelancerProfile();
        console.log(JSON.stringify(profile, null, 2));
      } else if (cmd === 'update_availability') {
        const result = await updateFreelancerAvailability(flags);
        console.log(JSON.stringify(result, null, 2));
      } else if (cmd === 'introspect') {
        await introspectType(rest[0] || 'RoomFilter');
      } else {
        console.log(`
  Commands:
    node upworkServices.js list [--filter '{}']
    node upworkServices.js conversations --roomId ID [--filter '{}']
    node upworkServices.js all_conversations [--filter '{}']
    node upworkServices.js send --roomId ID --text "msg" [--attachmentId "file_id"]
    node upworkServices.js get_profile
    node upworkServices.js update_availability --availability "AVAILABLE"|"NOT_AVAILABLE"
    node upworkServices.js introspect [RoomFilter | RoomStoryFilter | Freelancer | Mutation.updateFreelancerAvailability]
  `);
      }
    } catch (e) {
      console.error('Error:', e.message);
    }
  }

main();