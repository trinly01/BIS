// Ordered journey for the request timeline UI. Terminal/exceptional
// statuses (rejected, cancelled) render separately.
export const JOURNEY = [
  "received",
  "requirements_check",
  "for_payment",
  "for_signature",
  "released",
]

export const STATUS_LABEL = {
  received: "Received",
  requirements_check: "Requirements Check",
  for_payment: "For Payment",
  for_signature: "For Signature",
  released: "Released",
  rejected: "Rejected",
  cancelled: "Cancelled",
}

export const STATUS_DESC = {
  received: "Your request was received and is queued for processing.",
  requirements_check: "Staff are checking your requirements. You may be asked for supporting documents.",
  for_payment: "Requirements complete — please pay the fee at the barangay hall.",
  for_signature: "Document prepared — waiting for the Punong Barangay's signature.",
  released: "Document released. Please claim it at the barangay hall if not yet picked up.",
  rejected: "This request was rejected. See remarks or visit the barangay hall.",
  cancelled: "This request was cancelled.",
}

export function statusVariant(status) {
  if (status === "released") return "default"
  if (status === "rejected" || status === "cancelled") return "destructive"
  if (status === "for_signature" || status === "for_payment") return "warning"
  return "secondary"
}
