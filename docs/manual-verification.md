# Manual Verification Checklist

Use this checklist to verify the seeded scenarios, one live signal change, one fallback path, and the coach surface. Run `make setup && make dev` (or `curl -X POST http://127.0.0.1:8000/debug/reset-seed` to reset mid-session) before starting.

- Frontend: `http://localhost:5173`
- Backend: `http://127.0.0.1:8000`

---

## 1. Seeded Scenario: Meal Mismatch (Alice Chen)

- [ ] Open `/member?memberId=member_meal_01`
- [ ] Confirm an active nudge appears with meal-guidance content
- [ ] Confirm the "Why this may help" explanation references her low-carb goal and a higher-carb meal
- [ ] Click **"I will do this"** → confirmation message appears briefly → nudge resolves to the "All set" state with "Your routine looks steady today."
- [ ] Navigate to `/coach` → Alice's nudge appears in Recent Nudges with status **Acted**
- [ ] Expand the nudge row → confirm content, explanation, matched reason (`meal_goal_mismatch`), and confidence (`0.86`) are visible

## 2. Seeded Scenario: Missing Weight Log (Bob Martinez)

- [ ] Open `/member?memberId=member_weight_01`
- [ ] Confirm an active nudge appears prompting a weight check-in
- [ ] Confirm the explanation references not logging weight recently
- [ ] Click **"Not now"** → nudge is dismissed → state changes
- [ ] Navigate to `/coach` → Bob's nudge appears with status **Dismissed**

## 3. Seeded Scenario: Support Risk Escalation (Carol Davis)

- [ ] Open `/member?memberId=member_support_01`
- [ ] Confirm the member sees an escalated state — care team notification message, no actionable nudge card
- [ ] Navigate to `/coach` → an open escalation for Carol is visible
- [ ] Confirm escalation card shows source **Rule engine**, reason referencing low mood and dismissed nudges
- [ ] Confirm Carol's nudge also appears in the Recent Nudges list with status **Escalated**

## 4. Seeded Scenario: No Nudge (Diego Rivera)

- [ ] Open `/member?memberId=member_catchup_01`
- [ ] Confirm the member sees the "All set" state with "Your routine looks steady today." and no active nudge
- [ ] Confirm Diego does not appear in coach escalations

## 5. Live Signal: Weight Log Triggers Re-evaluation

- [ ] Reset seed (`POST /debug/reset-seed`)
- [ ] Open `/member?memberId=member_weight_01` → active weight check-in nudge visible
- [ ] Use the **Weight** quick-log form → enter a value (e.g., 180 lb) → submit
- [ ] Confirm toast notification appears confirming the log
- [ ] Confirm the weight-check-in nudge no longer appears and Bob returns to the no-nudge state

## 6. Live Signal: Mood Log

- [ ] Open `/member?memberId=member_catchup_01` (Diego, currently no nudge)
- [ ] Use the **Mood** quick-log form → select **Low** → submit
- [ ] Confirm toast notification appears
- [ ] Confirm Diego remains in the no-nudge state; low mood alone should not trigger support-risk without recent dismissals

## 7. Member-Initiated Escalation

- [ ] Reset seed
- [ ] Open `/member?memberId=member_weight_01` → active nudge visible
- [ ] Click **"I need support"** → nudge resolves to escalated state
- [ ] Navigate to `/coach` → new escalation for Bob appears with source **Member asked for help**
- [ ] Confirm Bob's escalation source is **Member asked for help** and Carol's seeded escalation remains **Rule engine**

## 8. Meal Photo Upload

- [ ] Open any member → scroll to the **Meal** quick-log card
- [ ] Upload a food photo → submit
- [ ] Confirm toast notification on success
- [ ] If no API key is configured, confirm the upload still succeeds and the app falls back to a conservative meal-analysis result

## 9. LLM Phrasing Fallback

- [ ] Ensure `OPENAI_API_KEY` is **not set** in `server/.env` (or set to empty)
- [ ] Reset seed
- [ ] Open `/member?memberId=member_meal_01`
- [ ] Confirm the nudge displays template phrasing: "Try a lighter, lower-carb dinner to balance today's earlier meal."
- [ ] Navigate to `/coach` → expand Alice's nudge → confirm `phrasing_source` shows **template**

## 10. Coach Surface: Structural Checks

- [ ] Navigate to `/coach`
- [ ] Confirm two sections are visible: **Escalations** and **Recent Nudges**
- [ ] Confirm escalation cards show member name, source, reason, status, and timestamp
- [ ] Confirm nudge list items are expandable and show confidence badge, status, matched reason, phrasing source, and latest member action (if any)
- [ ] Click **Refresh** → both sections reload

## 11. Responsive Spot-Check

- [ ] Open `/member` at desktop width (≥1024px) → layout is clean; quick-log shows 3 side-by-side cards/sections (weight, sleep, mood) with the meal log spanning the full row
- [ ] Resize to tablet width (~768px) → layout adapts, no horizontal overflow
- [ ] Resize to mobile width (~375px) → single-column, all content accessible, no truncation of nudge text
- [ ] Repeat for `/coach` — escalation grid and nudge list adapt to narrower widths

## 12. Keyboard Accessibility

- [ ] On `/member`, tab through the nudge action buttons → all three are focusable and activatable with Enter/Space
- [ ] On the member switcher, open the account menu via keyboard → move through the member links with Tab → activate a selection with Enter
- [ ] On quick-log forms, tab through inputs and submit buttons → forms are operable without a mouse
