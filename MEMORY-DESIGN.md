# Disha memory design

Two memories, deliberately separate. Mixing them is how voice agents leak one
student's life into another's call.

## 1. Conversation memory (room-scoped, verbatim)

What: every utterance, both directions, exactly as spoken/said.

- Producer: `agent/main.py` — `user_input_transcribed` (student, with detected
  language) and `conversation_item_added` (Disha) both emit
  `{"type":"utterance","role":"student"|"disha","text",...,"lang"}`.
- Store: `agent/cases/<room>.json` JSONL, append-only. Served read-only by
  `api/` for the counsellor view.
- Purpose: barge-in context (the LLM context already holds the live window —
  the log is the durable copy), counsellor audit ("what exactly was said"),
  and the corpus for later semantic search.
- Retention: per-room file; no audio, text only. Delete = delete the file.
- Qdrant layer (deferred, see HANDOFF-KB.md): embed utterances per case for
  semantic recall across long conversations. It indexes conversation memory;
  it never becomes a second source of personal facts.

## 2. Personal memory (student-scoped, distilled)

What: the few facts that should survive the call and shape guidance.

- Producer: explicit tool calls only — `save_constraint` (the five constraints)
  and `remember_student` (notable facts: "father is a farmer near Nashik").
  The LLM decides to write; nothing is scraped silently from transcripts.
- Store: same case file today (`constraint` / `note` events); keyed to a
  student when `disha.case` attribute lands (HANDOFF-KB Task 2).
- Purpose: resume without re-asking; the parent summary; counsellor context.
- Boundary rules:
  1. Distilled facts only — never transcripts, never quotes, never feelings.
  2. Wellbeing flags are NOT personal memory: they live as `flag` events for
     the counsellor queue and are never replayed back to the student.
  3. On resume, personal memory is loaded into the prompt; conversation memory
     is not (except a short last-session recap line).
  4. A second student on the same device must never see the first one's case:
     case id comes from the participant attribute, files are per-case, and the
     API serves by explicit case id only.

## Rubric mapping (do not double-count)

- In-call thread recovery after barge-in → Voice Experience evidence.
- Resume across sessions from personal memory → Memory & Context evidence.
- Counsellor audit trail from conversation memory → supports JTBD/trust.
