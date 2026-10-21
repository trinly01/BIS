// Public portal API — hits bis_portal_* / bis_verify_doc webhook flows.
// No auth: each flow validates input server-side and returns a sanitized
// payload only. Tracking uses request_no + registered mobile as the
// shared secret. Direct collection access is denied to public.
const BASE = "https://likha-playground.zyberlab.com/flows/trigger"
const OPTIONS_URL = `${BASE}/fb095790-b259-4c92-923c-e08d64d211fa`
const REQUEST_URL = `${BASE}/a784fb2d-6d92-4601-b7e0-8e278ba8c7db`
const TRACK_URL = `${BASE}/af009912-0030-49f1-abd8-aeb06c2aa6c7`
const VERIFY_URL = `${BASE}/8baa0787-7fe2-4a3c-b2f4-f774ee3c767d`

async function post(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error("Request failed (" + res.status + ")")
  const data = await res.json()
  return data
}

export async function getDocTypes() {
  const res = await fetch(OPTIONS_URL)
  if (!res.ok) throw new Error("Failed to load document types")
  const data = await res.json()
  return (data && data.types) || []
}

export async function submitRequest(payload) {
  return post(REQUEST_URL, payload)
}

export async function trackRequest(ref, key) {
  const data = await post(TRACK_URL, { ref, key })
  return data && data.found ? data.request : null
}

export async function verifyDoc(serial) {
  const res = await fetch(`${VERIFY_URL}?serial=${encodeURIComponent(serial)}`)
  if (!res.ok) throw new Error("Verification failed (" + res.status + ")")
  return res.json()
}
