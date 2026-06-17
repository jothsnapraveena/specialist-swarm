# Test Case Document — Talent Cortex

**Product:** Talent Cortex — AI-Powered Recruitment Swarm  
**Audience:** QA Engineers, Dev Team, Recruiters (UAT)  
**Status:** Draft v1.0  
**Date:** 2026-06-17  

---

## Table of Contents

1. [TC-SUBMIT — Drive Submission](#tc-submit--drive-submission-new-drive-screen)
2. [TC-POLL — Live Status Polling](#tc-poll--live-status-polling)
3. [TC-BG — Background Verification Gate](#tc-bg--background-verification-gate)
4. [TC-JD — JD Matching Gate](#tc-jd--jd-matching-gate)
5. [TC-PANEL — Panelist Matching](#tc-panel--panelist-matching)
6. [TC-EXPORT — DOCX Export](#tc-export--docx-export)
7. [TC-POOL — Panelist Pool Management](#tc-pool--panelist-pool-management)
8. [TC-ERROR — Error Handling & Retry](#tc-error--error-handling--retry)
9. [TC-GATE — Gate Enforcement (Server-Side)](#tc-gate--gate-enforcement-server-side)
10. [Test Coverage Summary](#test-coverage-summary)

---

## TC-SUBMIT — Drive Submission (New Drive Screen)

This section covers all scenarios for the New Drive submission form. It validates client-side input guards (AC-01.1, AC-01.2), the parallel API call pattern on valid submission (AC-01.3), and backend 400 rejection for blank payloads before any Anthropic session is started (AC-01.4, AC-01.5). Both UI-layer and API-layer behaviors are tested.

| ID | Title | Preconditions | Steps | Expected Result | Type | Priority |
|----|-------|---------------|-------|-----------------|------|----------|
| TC-SUBMIT-001 | Empty resume field blocked client-side | New Drive screen is open; JD field is populated with valid text | 1. Leave resume textarea blank. 2. Click "Start Drive". | Inline error "Resume text is required." appears beneath the resume field. No call to POST /candidates or POST /jobs is made. | e2e | P0 |
| TC-SUBMIT-002 | Empty JD field blocked client-side | New Drive screen is open; resume field is populated with valid text | 1. Leave JD textarea blank. 2. Click "Start Drive". | Inline error "Job description is required." appears beneath the JD field. No call to POST /candidates or POST /jobs is made. | e2e | P0 |
| TC-SUBMIT-003 | Both fields empty shows both inline errors | New Drive screen is open | 1. Leave both resume and JD fields blank. 2. Click "Start Drive". | Both inline errors are displayed simultaneously. No API calls are made. | e2e | P1 |
| TC-SUBMIT-004 | Valid inputs trigger parallel API calls then drive creation | New Drive screen is open; a panelist pool is already stored | 1. Enter valid resume text. 2. Enter valid JD text. 3. Click "Start Drive". | POST /candidates and POST /jobs are called in parallel. After both return, POST /drives is called with the returned candidate_id and job_id. UI navigates to the Drive Status screen for the new drive_id. | e2e | P0 |
| TC-SUBMIT-005 | Blank resume_text to backend returns HTTP 400 | Direct API access; no UI | 1. POST /candidates with body { "resume_text": "" }. | HTTP 400 is returned. No Anthropic session is initiated. | integration | P0 |
| TC-SUBMIT-006 | Blank jd_text to backend returns HTTP 400 | Direct API access; no UI | 1. POST /jobs with body { "jd_text": "" }. | HTTP 400 is returned. No Anthropic session is initiated. | integration | P0 |
| TC-SUBMIT-007 | Whitespace-only resume treated as blank | New Drive screen is open | 1. Enter only spaces/tabs in the resume textarea. 2. Click "Start Drive". | Inline error "Resume text is required." is shown. No API call is made (or backend returns 400 if passed through). | e2e | P1 |
| TC-SUBMIT-008 | POST /drives uses candidate_id and job_id from prior responses | Direct API access; valid candidate_id and job_id already obtained | 1. POST /drives with { "candidate_id": "<valid>", "job_id": "<valid>" }. | HTTP 200 with { drive_id } returned. Drive entry is created with status PENDING. | integration | P0 |

---

## TC-POLL — Live Status Polling

This section covers the frontend polling behavior for the Drive Status screen. It verifies that polling fires at the correct 2,500 ms interval (AC-02.1), that a pulsing indicator is shown during non-terminal states (AC-02.2), that polling halts immediately upon reaching any terminal status (AC-02.3), and that each stage row reflects the correct state label depending on the current drive status (AC-02.4 – AC-02.6).

| ID | Title | Preconditions | Steps | Expected Result | Type | Priority |
|----|-------|---------------|-------|-----------------|------|----------|
| TC-POLL-001 | Polling fires every 2,500 ms | Drive Status screen is open; drive is in a non-terminal status | 1. Observe network requests to GET /drives/{id} over a 10-second window. | GET /drives/{id} is called approximately every 2,500 ms (±200 ms tolerance). | e2e | P0 |
| TC-POLL-002 | Pulsing indicator visible during non-terminal status | Drive is in RUNNING_BACKGROUND_CHECK | 1. Open Drive Status screen. | A pulsing animation indicator is visible on the status display. | e2e | P1 |
| TC-POLL-003 | Polling stops immediately on terminal status COMPLETED | Drive transitions to COMPLETED during polling | 1. Open Drive Status screen. 2. Wait for drive to reach COMPLETED. | Polling calls stop. No further GET /drives/{id} requests are made after the terminal response is received. | e2e | P0 |
| TC-POLL-004 | Polling stops on REJECTED_BACKGROUND | Drive transitions to REJECTED_BACKGROUND | 1. Open Drive Status screen. 2. Wait for rejection. | Polling stops immediately after REJECTED_BACKGROUND is returned. | e2e | P0 |
| TC-POLL-005 | Polling stops on REJECTED_FIT | Drive transitions to REJECTED_FIT | 1. Open Drive Status screen. 2. Wait for rejection. | Polling stops immediately after REJECTED_FIT is returned. | e2e | P0 |
| TC-POLL-006 | Polling stops on HOLD_FIT | Drive transitions to HOLD_FIT | 1. Open Drive Status screen. 2. Wait for hold. | Polling stops immediately after HOLD_FIT is returned. | e2e | P0 |
| TC-POLL-007 | Polling stops on FAILED | Drive transitions to FAILED | 1. Open Drive Status screen. 2. Wait for failure. | Polling stops immediately after FAILED is returned. | e2e | P0 |
| TC-POLL-008 | Stage rows during RUNNING_BACKGROUND_CHECK | Drive status = RUNNING_BACKGROUND_CHECK | 1. Open Drive Status screen. | BG row shows "running". JD row shows "pending". Panel row shows "pending". | e2e | P1 |
| TC-POLL-009 | Stage rows during RUNNING_JD_MATCH | Drive status = RUNNING_JD_MATCH | 1. Open Drive Status screen. | BG row shows "passed". JD row shows "running". Panel row shows "pending". | e2e | P1 |
| TC-POLL-010 | Stage rows during RUNNING_PANEL_MATCH | Drive status = RUNNING_PANEL_MATCH | 1. Open Drive Status screen. | BG row shows "passed". JD row shows "passed". Panel row shows "running". | e2e | P1 |

---

## TC-BG — Background Verification Gate

This section covers the background verification specialist (AC-03.x). It tests both lanes of the check: Lane 1 (resume internal consistency — timeline, education, skills, contact info, contradictions) and Lane 2 (social/public profile corroboration). Key invariants are: a single blocker flag produces REJECTED_BACKGROUND and halts the pipeline; multiple minor flags alone do not produce a blocker; if no public profile data is supplied Lane 2 is skipped; and a LEGITIMATE verdict allows the pipeline to proceed to JD matching.

| ID | Title | Preconditions | Steps | Expected Result | Type | Priority |
|----|-------|---------------|-------|-----------------|------|----------|
| TC-BG-001 | Happy path — LEGITIMATE background allows pipeline to continue | Drive submitted with clean, internally consistent resume; no social contradictions | 1. Submit drive. 2. Poll until status advances past RUNNING_BACKGROUND_CHECK. | background_check.verdict = "LEGITIMATE". No flags of severity "blocker". Drive status advances to RUNNING_JD_MATCH. | integration | P0 |
| TC-BG-002 | Single blocker flag → REJECTED_BACKGROUND; JD and Panel never called | Resume with clear blocker (e.g., two concurrent "current" employers) | 1. Submit drive. 2. Poll until terminal. | Status = REJECTED_BACKGROUND. background_check.verdict = "REJECTED". Flags array contains at least one entry with severity "blocker". jd_match = null. panel_match = null. JD specialist is never invoked. Panel specialist is never invoked. | integration | P0 |
| TC-BG-003 | Multiple minor flags only → LEGITIMATE (minors do not accumulate to blocker) | Resume with several minor inconsistencies (e.g., slightly vague dates, informal education description) but no single blocker | 1. Submit drive. 2. Poll until background check completes. | background_check.verdict = "LEGITIMATE". All flags have severity below "blocker". Drive status advances to RUNNING_JD_MATCH. | integration | P1 |
| TC-BG-004 | No contact info at all → blocker flag | Resume contains no email address, phone number, or contactable identifier | 1. Submit drive with such a resume. 2. Poll until terminal. | Status = REJECTED_BACKGROUND. Flags contain a blocker-severity entry related to contact info validity. jd_match = null. panel_match = null. | integration | P0 |
| TC-BG-005 | Two simultaneous "current" employers → blocker | Resume lists two separate roles both marked as current/present | 1. Submit drive. 2. Poll until terminal. | Status = REJECTED_BACKGROUND. Flags contain a blocker-severity entry for employment timeline inconsistency. | integration | P0 |
| TC-BG-006 | Social profile employer contradicts resume → blocker | Resume claims Employer A; linked public profile shows Employer B for the same period | 1. Submit drive including public profile data that contradicts resume employer. 2. Poll until terminal. | Status = REJECTED_BACKGROUND. Flags contain a blocker-severity entry for profile vs resume inconsistency (Lane 2). | integration | P0 |
| TC-BG-007 | No public profile data supplied → Lane 2 skipped, Lane 1 evaluated | Resume submitted without any social/public profile URL or data | 1. Submit drive. 2. Poll until background check completes. | Lane 2 checks are not run. Lane 1 results are returned. background_check response does not contain Lane 2 findings. Drive verdict is based solely on Lane 1 outcome. | integration | P1 |
| TC-BG-008 | UI shows BG row "rejected" with blocker flags listed | Drive has reached REJECTED_BACKGROUND terminal status | 1. Open Drive Status screen for a REJECTED_BACKGROUND drive. | BG stage row displays label "rejected". Blocker flags from background_check.flags are listed in the UI detail. JD and Panel rows display as greyed/pending and are not clickable. | e2e | P1 |
| TC-BG-009 | Education plausibility failure → blocker | Resume claims a degree from an institution in a timeframe that is implausible (e.g., 4-year degree completed in 6 months) | 1. Submit drive. 2. Poll until terminal. | Flags contain blocker or high-severity entry for education plausibility. Depending on severity classification, either status = REJECTED_BACKGROUND or flag is minor. | integration | P2 |
| TC-BG-010 | Skill corroboration failure — minor flag only | Resume lists many advanced skills but experience descriptions are thin; not a single outright blocker | 1. Submit drive. 2. Poll. | background_check.verdict may be LEGITIMATE with minor skill-corroboration flags. Pipeline proceeds. | integration | P2 |

---

## TC-JD — JD Matching Gate

This section covers the JD matching specialist (AC-04.x, AC-05.x). It validates the three-outcome recommendation logic (PROCEED, HOLD, REJECT) based on the scoring formula: must-haves contribute 70 pts split evenly, nice-to-haves 30 pts. The caps rule is critical: a single missing must-have forces HOLD even when the computed score reaches or exceeds 70. For REJECT and HOLD, the panel specialist must never be called and panel_match must be null. For HOLD, the specific recruiter guidance message must appear in the UI.

| ID | Title | Preconditions | Steps | Expected Result | Type | Priority |
|----|-------|---------------|-------|-----------------|------|----------|
| TC-JD-001 | Score >= 70 and zero must-haves missing → PROCEED to panel | Drive has passed background check; JD with 2 must-haves; resume meets both and scores >= 70 | 1. Submit drive. 2. Poll until past RUNNING_JD_MATCH. | jd_match.recommendation = "PROCEED". Drive advances to RUNNING_PANEL_MATCH. panel_match is not null. | integration | P0 |
| TC-JD-002 | Score 45–69 → HOLD_FIT; panel never called | Drive has passed background check; resume achieves a JD score in the 45–69 range with all must-haves met | 1. Submit drive. 2. Poll until terminal. | Status = HOLD_FIT. jd_match.recommendation = "HOLD". jd_match.score is between 45 and 69 inclusive. panel_match = null. Panel specialist is never invoked. | integration | P0 |
| TC-JD-003 | Exactly one must-have missing with score >= 70 → HOLD (caps rule) | Drive has passed background check; JD has 2 must-haves; resume meets one fully, missing the other; nice-to-have scores push total >= 70 | 1. Submit drive. 2. Poll until terminal. | Status = HOLD_FIT. jd_match.recommendation = "HOLD". jd_match.missing_skills contains the single missing must-have. panel_match = null. Panel specialist is never invoked. | integration | P0 |
| TC-JD-004 | Two or more must-haves missing → REJECTED_FIT | Drive has passed background check; JD has 3 must-haves; resume is missing 2 | 1. Submit drive. 2. Poll until terminal. | Status = REJECTED_FIT. jd_match.recommendation = "REJECT". jd_match.missing_skills lists the 2+ missing must-haves. panel_match = null. Panel specialist is never invoked. | integration | P0 |
| TC-JD-005 | Score < 45 → REJECTED_FIT | Drive has passed background check; resume achieves JD score below 45 | 1. Submit drive. 2. Poll until terminal. | Status = REJECTED_FIT. jd_match.recommendation = "REJECT". jd_match.score < 45. panel_match = null. | integration | P0 |
| TC-JD-006 | REJECT → panel_match is null in API response | Drive has reached REJECTED_FIT | 1. GET /drives/{id}. | Response body: panel_match = null (or absent). | integration | P0 |
| TC-JD-007 | HOLD → recruiter guidance message shown in UI | Drive has reached HOLD_FIT | 1. Open Drive Status screen. | JD stage row shows "hold". Detail card displays fit score, skill gaps, and the message "Cancel and resubmit with an updated JD or candidate profile to proceed." | e2e | P1 |
| TC-JD-008 | HOLD → panel_match is null in API response | Drive has reached HOLD_FIT | 1. GET /drives/{id}. | Response body: panel_match = null (or absent). | integration | P0 |
| TC-JD-009 | UI: REJECTED_FIT shows score and missing skills | Drive has reached REJECTED_FIT | 1. Open Drive Status screen. | JD stage row shows "rejected". Detail card shows jd_match.score and the list of missing skills. Panel row remains greyed. | e2e | P1 |
| TC-JD-010 | Partial must-have credit applied correctly | Drive has passed background check; resume partially meets a must-have (partial credit = half points for that must-have) | 1. Submit drive. 2. GET /drives/{id} after JD stage completes. | jd_match.score reflects partial credit (half points for the partially met must-have). Recommendation is determined by final total and missing count. | integration | P2 |

---

## TC-PANEL — Panelist Matching

This section covers the panelist matching specialist (AC-06.x, AC-07.x). Panelist selection follows a fixed three-step decision order: (1) skill overlap is the primary ranking criterion and zero-overlap panelists are excluded outright; (2) availability is a secondary tiebreaker applied only among equal-overlap candidates; (3) mode (In-Person or Online) is determined per panelist independently based on location match. A fully empty slate after filtering is a valid COMPLETED outcome, not an error.

| ID | Title | Preconditions | Steps | Expected Result | Type | Priority |
|----|-------|---------------|-------|-----------------|------|----------|
| TC-PANEL-001 | Skill overlap is primary criterion — higher overlap panelist wins | Panelist A has 4 overlapping skills; Panelist B has 1 overlapping skill; both are available | 1. Submit drive that proceeds to panel stage. 2. GET /drives/{id}/report. | Panelist A is ranked above Panelist B in the panel_slate. | integration | P0 |
| TC-PANEL-002 | Zero-overlap panelist excluded even if most available | Panelist A has 0 skill overlap but many open slots; Panelist B has 2 overlapping skills with limited availability | 1. Submit drive proceeding to panel. 2. GET /drives/{id}/report. | Panelist A is not in panel_slate. Panelist B is included. | integration | P0 |
| TC-PANEL-003 | Equal skill overlap → availability is tiebreaker | Panelist A and B both have 3 overlapping skills; Panelist A has 5 available slots; Panelist B has 1 | 1. Submit drive proceeding to panel. 2. GET /drives/{id}/report. | Panelist A is ranked above Panelist B due to more availability. | integration | P1 |
| TC-PANEL-004 | Location match → mode = "In-Person" | Candidate location = "New York"; Panelist location = "New York"; panelist has skill overlap | 1. Submit drive proceeding to panel. 2. GET /drives/{id}/report. | Panelist entry has mode = "In-Person" and reason includes location-match justification. | integration | P1 |
| TC-PANEL-005 | Location mismatch → mode = "Online" | Candidate location = "New York"; Panelist location = "San Francisco"; panelist has skill overlap | 1. Submit drive proceeding to panel. 2. GET /drives/{id}/report. | Panelist entry has mode = "Online" and reason includes location-mismatch justification. | integration | P1 |
| TC-PANEL-006 | Mixed-mode panel is valid | Pool has Panelist A (location match) and Panelist B (location mismatch); both have skill overlap | 1. Submit drive proceeding to panel. 2. GET /drives/{id}/report. | Panelist A has mode = "In-Person"; Panelist B has mode = "Online". Both appear in panel_slate. Status = COMPLETED. | integration | P1 |
| TC-PANEL-007 | Empty panel slate → status COMPLETED, not FAILED | All panelists in pool have zero skill overlap with the candidate | 1. Submit drive that passes BG and JD checks. 2. Poll until terminal. | Status = COMPLETED. panel_slate = []. No error is raised. GET /drives/{id}/report returns a valid report with an empty panel_slate. | integration | P0 |
| TC-PANEL-008 | Empty panel slate → UI shows explicit message | Drive has COMPLETED with empty panel_slate | 1. Open Drive Status screen or report view. | UI displays "No panelist cleared both criteria." No empty table rows are rendered for panelists. | e2e | P1 |
| TC-PANEL-009 | COMPLETED → GET /drives/{id}/report returns full report shape | Drive has reached COMPLETED with non-empty panel_slate | 1. GET /drives/{id}/report (default or format=json). | Response contains background_check, jd_match, and panel_match sections. panel_match.panel_slate is a non-empty array. Each panelist entry includes name, skill_overlap, availability, mode, and reason. | integration | P0 |
| TC-PANEL-010 | Availability secondary — never loosens skill criterion | Panelist A has 1 overlap, 10 availability slots; Panelist B has 3 overlap, 0 availability slots | 1. Submit drive proceeding to panel. 2. GET /drives/{id}/report. | Panelist A is ranked below B by skill. If Panelist B has no open slot, Panelist B is excluded. Panelist A (lower skill overlap) is not promoted over B due to availability. | integration | P1 |

---

## TC-EXPORT — DOCX Export

This section covers the DOCX export feature (AC-08.x). It verifies that clicking the export button triggers the correct API call and that the browser receives a binary DOCX file. Both the UI trigger path and the direct API path are tested.

| ID | Title | Preconditions | Steps | Expected Result | Type | Priority |
|----|-------|---------------|-------|-----------------|------|----------|
| TC-EXPORT-001 | "Export (DOCX)" button triggers correct API call | Drive has reached COMPLETED; report view is open | 1. Click "Export (DOCX)" button. | Browser sends GET /drives/{id}/report?format=docx. | e2e | P0 |
| TC-EXPORT-002 | DOCX response is a binary file with correct content type | Drive has reached COMPLETED | 1. GET /drives/{id}/report?format=docx. | HTTP 200 returned. Response Content-Type is application/vnd.openxmlformats-officedocument.wordprocessingml.document. Response body is non-empty binary. | integration | P0 |
| TC-EXPORT-003 | Browser downloads DOCX file (not renders inline) | Drive has reached COMPLETED; UI export button clicked | 1. Click "Export (DOCX)". | Browser initiates a file download. User receives a .docx file. No browser tab opens with rendered content. | e2e | P1 |
| TC-EXPORT-004 | JSON report format is default or explicit | Drive has reached COMPLETED | 1. GET /drives/{id}/report (no format param). 2. GET /drives/{id}/report?format=json. | Both return HTTP 200 with JSON body containing background_check, jd_match, and panel_match sections. | integration | P1 |
| TC-EXPORT-005 | Export unavailable for non-terminal or non-COMPLETED drives | Drive is in RUNNING_PANEL_MATCH or REJECTED_BACKGROUND | 1. Attempt GET /drives/{id}/report?format=docx for a non-COMPLETED drive. | Response is either HTTP 409/422 indicating drive is not in a reportable state, or the export button is disabled/absent in the UI. | integration | P2 |

---

## TC-POOL — Panelist Pool Management

This section covers the panelist pool management screen (AC-09.x). It validates reading and displaying the pool, client-side JSON validation before PUT is called, rejection of valid JSON that is not an array, and the success flow with banner and table refresh. Client-side guards must prevent the PUT call from being made when validation fails.

| ID | Title | Preconditions | Steps | Expected Result | Type | Priority |
|----|-------|---------------|-------|-----------------|------|----------|
| TC-POOL-001 | GET panelists renders table with all fields | Pool has been pre-populated with at least 2 panelists | 1. Open Panelist Pool management screen. | Table shows one row per panelist. Each row displays name, location, skills as tag list, and availability slots. | e2e | P1 |
| TC-POOL-002 | Invalid JSON in textarea → client-side error, PUT not called | Panelist pool screen is open | 1. Enter malformed JSON (e.g., `{ name: "Alice" `) in the textarea. 2. Click Save. | Error message "Invalid JSON — fix the syntax and try again." is shown. PUT /panelists is NOT called. | e2e | P0 |
| TC-POOL-003 | Valid JSON but not an array → client-side error, PUT not called | Panelist pool screen is open | 1. Enter valid JSON object `{ "name": "Alice" }` (not an array) in textarea. 2. Click Save. | Error message "Pool must be a JSON array." is shown. PUT /panelists is NOT called. | e2e | P0 |
| TC-POOL-004 | Valid JSON array → PUT called, success banner shown, table refreshed | Panelist pool screen is open | 1. Enter a valid JSON array of panelist objects in textarea. 2. Click Save. | PUT /panelists is called with the array. HTTP 200 received. "Pool saved successfully." banner is displayed. Table re-renders to reflect the new pool. | e2e | P0 |
| TC-POOL-005 | PUT /panelists with malformed body → HTTP 400 | Direct API access | 1. PUT /panelists with body that is not a valid JSON array (e.g., a plain string). | HTTP 400 returned. Pool is not modified. | integration | P1 |
| TC-POOL-006 | Empty JSON array clears pool | Panelist pool screen is open | 1. Enter `[]` in textarea. 2. Click Save. | PUT /panelists is called with `[]`. Pool is saved as empty. Table shows zero rows (or explicit empty message). "Pool saved successfully." banner shown. | e2e | P2 |
| TC-POOL-007 | GET /panelists returns empty array when pool is empty | No panelists have been saved | 1. GET /panelists. | HTTP 200 with response body `[]`. | integration | P2 |

---

## TC-ERROR — Error Handling & Retry

This section covers error handling and retry paths (AC-10.x). It verifies that an Anthropic API error at any pipeline stage results in status = FAILED with an error field populated and no further specialist calls made. It also tests the polling HTTP error path, the "Start New Drive" recovery UI, and the retry behavior that reuses existing candidate and job IDs without re-uploading.

| ID | Title | Preconditions | Steps | Expected Result | Type | Priority |
|----|-------|---------------|-------|-----------------|------|----------|
| TC-ERROR-001 | Anthropic API error mid-background-check → FAILED | Drive is submitted; Anthropic API is configured to return an error during background check | 1. Submit drive. 2. Poll until terminal. | Status = FAILED. drive.error field is populated with error details. JD specialist is never invoked. Panel specialist is never invoked. | integration | P0 |
| TC-ERROR-002 | Anthropic API error mid-JD-match → FAILED | Drive has passed background check; Anthropic API returns error during JD match | 1. Submit drive. 2. Poll until terminal. | Status = FAILED. drive.error field is populated. Panel specialist is never invoked. | integration | P0 |
| TC-ERROR-003 | Anthropic API error mid-panel-match → FAILED | Drive has passed BG and JD checks; Anthropic API returns error during panel match | 1. Submit drive. 2. Poll until terminal. | Status = FAILED. drive.error field is populated. No further API calls are made after the failure. | integration | P0 |
| TC-ERROR-004 | Poll HTTP 500 → polling stops, error UI shown | Drive Status screen is open; next poll returns HTTP 500 | 1. Open Drive Status screen. 2. Simulate server returning HTTP 500 on GET /drives/{id}. | Polling stops. UI displays an error message describing the poll failure. No further poll requests are made. | e2e | P0 |
| TC-ERROR-005 | FAILED status shows "Start New Drive" button | Drive has reached FAILED status | 1. Open Drive Status screen for a FAILED drive. | UI shows the error message from drive.error. A "Start New Drive" button is visible and clickable. | e2e | P0 |
| TC-ERROR-006 | Retry via "Start New Drive" navigates to New Drive screen | Drive Status screen shows FAILED with "Start New Drive" button | 1. Click "Start New Drive". | User is taken to the New Drive submission form with blank fields. New POST /candidates and POST /jobs calls will be made on the next valid submission. | e2e | P1 |
| TC-ERROR-007 | Retry for known candidate/job reuses existing IDs | candidate_id and job_id are already stored from a prior run | 1. POST /drives directly with the existing candidate_id and job_id (no re-upload). | HTTP 200 with new drive_id. A new drive pipeline is started without requiring re-upload of resume or JD text. | integration | P1 |
| TC-ERROR-008 | Poll network timeout → error shown, polling stops | Drive Status screen is open; network request to GET /drives/{id} times out | 1. Open Drive Status screen. 2. Simulate network timeout on poll request. | Polling stops. UI shows an error or network-failure message. "Start New Drive" button is present. | e2e | P1 |

---

## TC-GATE — Gate Enforcement (Server-Side)

This section verifies server-side gate enforcement as a cross-cutting concern — independent of any UI or model instruction. The server must enforce pipeline stops itself: a REJECTED_BACKGROUND drive must never trigger downstream JD or Panel specialist calls; a REJECTED_FIT drive must never trigger Panel specialist calls. Additionally, drive status must only advance through legal transitions defined by the state machine and no state skipping is permitted.

| ID | Title | Preconditions | Steps | Expected Result | Type | Priority |
|----|-------|---------------|-------|-----------------|------|----------|
| TC-GATE-001 | REJECTED_BACKGROUND → no JD specialist call, verified server-side | Drive has reached REJECTED_BACKGROUND; server-side call log or mock available | 1. Inspect server execution log or mock invocation records after drive completes. | No call to the JD matching specialist is present in the log. No call to the panel matching specialist is present. | integration | P0 |
| TC-GATE-002 | REJECTED_FIT → no Panel specialist call, verified server-side | Drive has reached REJECTED_FIT; server-side call log or mock available | 1. Inspect server execution log or mock invocation records after drive completes. | No call to the panel matching specialist is present in the log. | integration | P0 |
| TC-GATE-003 | State cannot skip from PENDING directly to COMPLETED | Direct API or internal manipulation attempt | 1. Attempt to set drive status to COMPLETED while current status is PENDING (bypassing BG and JD stages). | Server rejects the transition. Drive status remains PENDING or returns an error. | integration | P0 |
| TC-GATE-004 | State cannot skip from RUNNING_BACKGROUND_CHECK to RUNNING_PANEL_MATCH | Direct API or internal manipulation attempt | 1. Attempt to set drive status to RUNNING_PANEL_MATCH while current status is RUNNING_BACKGROUND_CHECK. | Server rejects the illegal transition. Status does not advance to RUNNING_PANEL_MATCH. | integration | P1 |
| TC-GATE-005 | Terminal status cannot be overwritten | Drive has reached REJECTED_BACKGROUND (terminal) | 1. Attempt to update the drive status to any non-terminal or different terminal state. | Server rejects the update. Status remains REJECTED_BACKGROUND. | integration | P0 |
| TC-GATE-006 | REJECTED_BACKGROUND response body enforces null fields | Drive has reached REJECTED_BACKGROUND | 1. GET /drives/{id}. | Response: background_check.verdict = "REJECTED", jd_match = null, panel_match = null. | integration | P0 |
| TC-GATE-007 | REJECTED_FIT response body enforces null panel_match | Drive has reached REJECTED_FIT | 1. GET /drives/{id}. | Response: jd_match.recommendation = "REJECT", panel_match = null. | integration | P0 |

---

## Test Coverage Summary

| Area | # Cases | P0 | P1 | P2 | P3 |
|------|---------|----|----|----|----|
| TC-SUBMIT — Drive Submission | 8 | 5 | 2 | 1 | 0 |
| TC-POLL — Live Status Polling | 10 | 5 | 5 | 0 | 0 |
| TC-BG — Background Verification Gate | 10 | 5 | 3 | 2 | 0 |
| TC-JD — JD Matching Gate | 10 | 6 | 3 | 1 | 0 |
| TC-PANEL — Panelist Matching | 10 | 4 | 5 | 1 | 0 |
| TC-EXPORT — DOCX Export | 5 | 2 | 2 | 1 | 0 |
| TC-POOL — Panelist Pool Management | 7 | 3 | 2 | 2 | 0 |
| TC-ERROR — Error Handling & Retry | 8 | 4 | 3 | 0 | 0 |
| TC-GATE — Gate Enforcement (Server-Side) | 7 | 5 | 2 | 0 | 0 |
| **TOTAL** | **75** | **39** | **27** | **8** | **0** |
