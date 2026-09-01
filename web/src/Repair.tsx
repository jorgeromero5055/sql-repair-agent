import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { diffLines } from "diff";
import {
  getRepair,
  approveRepair,
  rejectRepair,
  type RepairDetail,
  type Attempt,
  type Row,
} from "./api";

// Shows what the agent changed. The library works out which lines were added, removed or left
// alone; we only colour them. A chunk can span several lines, which is why each chunk gets split
// before rendering — every line needs its own colour.
function Diff({ before, after }: { before: string; after: string }) {
  const parts = diffLines(before, after);

  return (
    <pre className="diff">
      {parts.flatMap((part, i) =>
        part.value
          .replace(/\n$/, "")
          .split("\n")
          .map((line, j) => (
            <div
              key={`${i}-${j}`}
              className={part.added ? "added" : part.removed ? "removed" : ""}
            >
              <span className="marker">
                {part.added ? "+" : part.removed ? "-" : " "}
              </span>
              {line}
            </div>
          )),
      )}
    </pre>
  );
}

// The rows the fixed query returns right now. The API works these out fresh on every request
// (see app/review.py), so what you see here is current, not a saved copy. Ten rows is a glance,
// which is all this needs to be — the full result is not the point.
function Preview({ rows }: { rows: Row[] }) {
  const columns = Object.keys(rows[0]);

  return (
    <table className="preview">
      <thead>
        <tr>
          {columns.map((c) => (
            <th key={c}>{c}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.slice(0, 10).map((row, i) => (
          <tr key={i}>
            {columns.map((c) => (
              <td key={c}>{String(row[c])}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// One attempt, closed until you click it. The API groups the statements by attempt for us
// (see app/review.py) — they're stored as one flat list and regrouped on the way out.
function AttemptBlock({ attempt }: { attempt: Attempt }) {
  return (
    <details className="attempt">
      <summary>
        Attempt {attempt.attempt} — {attempt.passed ? "passed" : "failed"}
        {attempt.reason ? `: ${attempt.reason}` : ""}
      </summary>
      {attempt.statements.map((s, i) => (
        <pre key={i} className={s.ok ? "sql" : "sql failed"}>
          {s.sql}
        </pre>
      ))}
    </details>
  );
}

export default function Repair() {
  const { id } = useParams();
  const [repair, setRepair] = useState<RepairDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  // Kept out of the effect below on purpose: a decision needs to run this again afterwards,
  // and code inside an effect only runs when the page opens.
  async function load() {
    try {
      setRepair(await getRepair(id!));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    load();
  }, [id]);

  // Approve and reject are the same except for which call they make. Everything around the call
  // is identical — clear the error, run it, reload so the new status shows, stop being busy — so
  // the call itself is the argument. Reloading is what updates the screen; it never guesses.
  async function decide(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
    setBusy(false);
  }

  // Only a failure to LOAD blanks the page. A failed decision keeps the repair on screen and
  // shows its message next to the buttons — you'd otherwise lose the thing you were deciding on.
  if (error && !repair) return <p>Couldn't load this repair: {error}</p>;
  if (!repair) return <p>Loading…</p>;

  // Convenience only. This enforces nothing — if it were wrong and the buttons showed, the
  // server would still refuse. The real rule is in api/app/approval.py.
  const decidable = repair.status === "needs_review";

  return (
    <>
      <p>
        <Link to="/queue">← Queue</Link>
      </p>

      <h1>{repair.intent}</h1>
      <p className={`status ${repair.status}`}>{repair.status.replace("_", " ")}</p>

      {repair.status === "rejected" && repair.rejection_reason && (
        <p className="rejected-reason">You rejected this: {repair.rejection_reason}</p>
      )}

      {/* No fixed query means the agent never got there — show what it was given instead. */}
      {repair.fixed_query ? (
        <>
          <h2>What changed</h2>
          <Diff before={repair.broken_query} after={repair.fixed_query} />
        </>
      ) : (
        <>
          <h2>The query it was given</h2>
          <pre className="sql">{repair.broken_query}</pre>
          <p>The agent never produced a fix.</p>
        </>
      )}

      {repair.explanation && (
        <>
          <h2>Why</h2>
          <p>{repair.explanation}</p>
        </>
      )}

      <h2>What it returns</h2>
      {repair.preview && repair.preview.length > 0 ? (
        <Preview rows={repair.preview} />
      ) : (
        <p>Nothing to show — the query returns no rows, or no longer runs.</p>
      )}

      <h2>What it tried</h2>
      {repair.attempts.length === 0 ? (
        <p>No attempts were recorded.</p>
      ) : (
        repair.attempts.map((a) => <AttemptBlock key={a.attempt} attempt={a} />)
      )}

      {repair.trace && (
        <p className="trace-summary">
          {repair.trace.attempts} attempts · {repair.trace.turns} turns ·{" "}
          {repair.trace.tokens} tokens · {repair.trace.latency_ms ?? "?"} ms
          {repair.trace.failure_reason ? ` · ${repair.trace.failure_reason}` : ""}
        </p>
      )}

      {decidable && (
        <div className="decision">
          <h2>Your decision</h2>

          <button
            disabled={busy}
            onClick={() => decide(() => approveRepair(repair.id))}
          >
            Approve and run it
          </button>

          <div className="reject">
            <label htmlFor="reason">Or reject it, and say why</label>
            <input
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="What's wrong with it?"
            />
            <button
              disabled={busy || reason.trim() === ""}
              onClick={() => decide(() => rejectRepair(repair.id, reason))}
            >
              Reject
            </button>
          </div>

          {error && <p className="error">{error}</p>}
        </div>
      )}
    </>
  );
}
