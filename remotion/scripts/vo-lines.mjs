/**
 * Voiceover lines — "B-I-S" is spelled out so TTS says "Bee Ay Ess".
 * Commas/ellipses add natural pauses. Regenerate: node scripts/gen-vo.mjs
 * Voice: fil-PH-AngeloNeural, rate +8%.
 */
export const LINES = {
  // BisAd
  s1_pain:  "Pila sa barangay hall? ... Balik-balik lang, para sa clearance? ... Not anymore.",
  s2_intro: "Meet Bee Ay Ess... the Barangay Information System. Government services, made easy.",
  s3_step1: "Step one: request online. Fill the form, pick your barangay and document... done in a minute.",
  s4_step2: "Step two: track it with your mobile. Request number plus mobile number... no lining up.",
  s5_step3: "Step three: claim your certificate. The QR code proves it's legit... anywhere.",
  s6_outro: "Your barangay... digital. San Fabian, Pangasinan.",

  // BisTutorial (s2_intro reused as the opening)
  t1_home:   "Here's how easy it is. Step one... open the Bis portal, and tap, Request a Document.",
  t2_form:   "Step two... pick your barangay, and document type... then your name, and mobile.",
  t3_submit: "Step three... submit. May request number ka agad, pati release date.",
  t4_track:  "Track it anytime... request number, plus your mobile. Walang pila, walang hulaan.",
  t5_admin:  "Behind the scenes, your barangay staff see it, on their dashboard... review, collect, print, release.",
  t6_verify: "Your certificate carries a QR code. Scan it, to verify. That's Bee Ay Ess.",
  t7_features: "And that's not all. Resident and household registry, blotter and mediation records, business permits, announcements... plus barangay assets, and benefits tracking.",
  t8_analytics: "For admins: live dashboards. Resident stats, incident heatmaps, document trends... per barangay, or municipality-wide.",
};
