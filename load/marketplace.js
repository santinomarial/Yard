import http from "k6/http";
import ws from "k6/ws";
import encoding from "k6/encoding";
import { check, sleep } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

const baseURL = __ENV.YARD_BASE_URL || "http://host.docker.internal:8000";
const websocketURL = baseURL.replace(/^http/, "ws");
const smoke = (__ENV.YARD_LOAD_PROFILE || "benchmark") === "smoke";
const png = encoding.b64decode(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nWQAAAAASUVORK5CYII=",
  "std"
);

const reservationWinners = new Counter("reservation_winners");
const reservationUnexpected = new Counter("reservation_unexpected");
const chatDelivered = new Rate("chat_delivered");
const publicationSucceeded = new Rate("publication_succeeded");
const browseLatency = new Trend("browse_latency", true);
const searchLatency = new Trend("search_latency", true);
const detailLatency = new Trend("detail_latency", true);

export const options = {
  scenarios: smoke
    ? {
        browse: { executor: "shared-iterations", exec: "browse", vus: 1, iterations: 2 },
        reservation: {
          executor: "shared-iterations", exec: "reserve", vus: 4, iterations: 4,
          startTime: "1s",
        },
        chat: { executor: "shared-iterations", exec: "chat", vus: 1, iterations: 1, startTime: "2s" },
        publication: {
          executor: "shared-iterations", exec: "publish", vus: 1, iterations: 1,
          startTime: "3s",
        },
      }
    : {
        browse: { executor: "constant-vus", exec: "browse", vus: 4, duration: "30s" },
        reservation: {
          executor: "shared-iterations", exec: "reserve", vus: 6, iterations: 6,
          startTime: "2s",
        },
        chat: {
          executor: "constant-arrival-rate", exec: "chat", rate: 2, timeUnit: "1s",
          duration: "20s", preAllocatedVUs: 3, startTime: "3s",
        },
        publication: {
          executor: "per-vu-iterations", exec: "publish", vus: 2, iterations: 2,
          maxDuration: "45s", startTime: "4s",
        },
      },
  thresholds: {
    http_req_duration: ["p(95)<750"],
    http_req_failed: ["rate<0.02"],
    reservation_winners: ["count==1"],
    reservation_unexpected: ["count==0"],
    chat_delivered: ["rate>0.98"],
    publication_succeeded: ["rate>0.98"],
  },
};

function jsonHeaders(token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  return { headers };
}

function signInFixture(id) {
  const response = http.post(
    `${baseURL}/api/v1/auth/development`,
    JSON.stringify({ display_name: `Load ${id}`, fixture_id: id }),
    jsonHeaders()
  );
  if (response.status !== 200) throw new Error(`fixture sign-in failed: ${response.status}`);
  const body = response.json();
  if (!body.user.harvard_email_verified) {
    const email = `${id}@harvard.edu`;
    const requested = http.post(
      `${baseURL}/api/v1/auth/verification/request`, JSON.stringify({ email }),
      jsonHeaders(body.access_token)
    );
    if (requested.status !== 200) throw new Error(`fixture verification failed: ${requested.status}`);
    const verified = http.post(
      `${baseURL}/api/v1/auth/verification/confirm`,
      JSON.stringify({ email, code: requested.json().development_code }),
      jsonHeaders(body.access_token)
    );
    if (verified.status !== 200) throw new Error(`fixture confirmation failed: ${verified.status}`);
  }
  return body.access_token;
}

function publicUploadURL(value) {
  return value.replace("http://localhost:", "http://host.docker.internal:");
}

function createAndPublish(token, categoryID, suffix) {
  const draft = http.post(
    `${baseURL}/api/v1/listings`,
    JSON.stringify({
      title: `Load test lamp ${suffix}`,
      description: "Fictional fixture used only for a documented local reliability test.",
      category_id: categoryID,
      price_cents: 1200,
      is_free: false,
      condition: "good",
      pickup_zone: "Harvard Square",
    }),
    jsonHeaders(token)
  );
  if (draft.status !== 201) return { ok: false, stage: "draft", status: draft.status };

  const listing = draft.json();
  const uploadRequest = http.post(
    `${baseURL}/api/v1/listings/${listing.id}/images/uploads`,
    JSON.stringify({ content_type: "image/png", byte_size: png.byteLength, sort_order: 0 }),
    jsonHeaders(token)
  );
  if (uploadRequest.status !== 201) {
    return { ok: false, stage: "upload-request", status: uploadRequest.status };
  }
  const upload = uploadRequest.json();
  const uploadHeaders = { ...upload.required_headers, Host: "localhost:9000" };
  const uploaded = http.put(publicUploadURL(upload.upload_url), png, {
    headers: uploadHeaders,
  });
  if (uploaded.status !== 200) return { ok: false, stage: "upload", status: uploaded.status };

  const completed = http.post(
    `${baseURL}/api/v1/listings/${listing.id}/images/${upload.image.id}/complete`,
    null,
    jsonHeaders(token)
  );
  if (completed.status !== 200) {
    return { ok: false, stage: "moderation", status: completed.status };
  }
  const submitted = http.post(
    `${baseURL}/api/v1/listings/${listing.id}/submit`, null, jsonHeaders(token)
  );
  return {
    ok: submitted.status === 200,
    stage: "submit",
    status: submitted.status,
    listing: submitted.status === 200 ? submitted.json() : null,
    responseBody: submitted.status === 200 ? undefined : submitted.body,
  };
}

export function setup() {
  const buyers = [];
  for (let index = 0; index < 6; index += 1) buyers.push(signInFixture(`load-buyer-${index}`));
  const seller = signInFixture("load-seller");
  const categories = http.get(`${baseURL}/api/v1/categories`).json();
  if (!categories.length) throw new Error("seed categories before running k6");
  const stamp = Date.now();
  const readFixture = createAndPublish(seller, categories[0].id, `read-${stamp}`);
  const contentionFixture = createAndPublish(seller, categories[0].id, `reserve-${stamp}`);
  if (!readFixture.ok || !contentionFixture.ok) {
    throw new Error(`could not publish load fixtures: ${JSON.stringify({ readFixture, contentionFixture })}`);
  }
  const conversation = http.post(
    `${baseURL}/api/v1/conversations`,
    JSON.stringify({ listing_id: readFixture.listing.id }),
    jsonHeaders(buyers[0])
  );
  if (conversation.status !== 201) throw new Error(`conversation fixture failed: ${conversation.status}`);
  return {
    buyers,
    seller,
    categoryID: categories[0].id,
    readListingID: readFixture.listing.id,
    reservationListingID: contentionFixture.listing.id,
    conversationID: conversation.json().id,
  };
}

export function browse(data) {
  const browseResponse = http.get(`${baseURL}/api/v1/listings?sort=newest`);
  browseLatency.add(browseResponse.timings.duration);
  check(browseResponse, { "browse succeeds": (response) => response.status === 200 });

  const searchResponse = http.get(`${baseURL}/api/v1/listings?query=lamp+under+25`);
  searchLatency.add(searchResponse.timings.duration);
  check(searchResponse, { "search succeeds": (response) => response.status === 200 });

  const detailResponse = http.get(`${baseURL}/api/v1/listings/${data.readListingID}`);
  detailLatency.add(detailResponse.timings.duration);
  check(detailResponse, { "listing detail succeeds": (response) => response.status === 200 });
  sleep(1);
}

export function reserve(data) {
  const token = data.buyers[(__VU - 1) % data.buyers.length];
  const response = http.post(
    `${baseURL}/api/v1/reservations`,
    JSON.stringify({ listing_id: data.reservationListingID, idempotency_key: `k6-${__VU}-${__ITER}-${Date.now()}` }),
    { ...jsonHeaders(token), responseCallback: http.expectedStatuses(200, 201, 409) }
  );
  if (response.status === 200 || response.status === 201) reservationWinners.add(1);
  else if (response.status !== 409) reservationUnexpected.add(1);
  check(response, { "reservation is winner or clean conflict": (item) => [200, 201, 409].includes(item.status) });
}

export function chat(data) {
  const result = ws.connect(
    `${websocketURL}/api/v1/conversations/${data.conversationID}/ws`,
    { headers: { Authorization: `Bearer ${data.buyers[0]}` } },
    (socket) => {
      socket.on("open", () => socket.send(JSON.stringify({ body: `k6 delivery ${Date.now()}` })));
      socket.on("message", (message) => {
        const delivered = JSON.parse(message);
        chatDelivered.add(delivered.conversation_id === data.conversationID);
        socket.close();
      });
      socket.setTimeout(() => { chatDelivered.add(false); socket.close(); }, 5000);
    }
  );
  check(result, { "websocket upgrades": (response) => response && response.status === 101 });
}

export function publish(data) {
  const result = createAndPublish(data.seller, data.categoryID, `scenario-${__VU}-${__ITER}-${Date.now()}`);
  publicationSucceeded.add(result.ok);
  check(result, { "listing publication succeeds": (value) => value.ok });
}
