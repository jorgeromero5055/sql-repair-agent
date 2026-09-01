import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  useNavigate,
} from "react-router-dom";
import { useEffect, useState } from "react";
import { createRepair, listRepairs, type RepairListItem } from "./api";
import Repair from "./Repair";

function Queue() {
  const [repairs, setRepairs] = useState<RepairListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await listRepairs();
        if (!cancelled) setRepairs(data);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    }

    load();
    const timer = setInterval(() => {
      const busy = repairs?.some(
        (r) => r.status === "queued" || r.status === "running"
      );
      if (busy) load();
    }, 3000);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [repairs]);

  if (error) return <p>Couldn't load repairs: {error}</p>;
  if (repairs === null) return <p>Loading…</p>;

  if (repairs.length === 0) {
    return (
      <>
        <h1>Queue</h1>
        <p>
          Nothing here yet. Paste a broken SQL query and say what it was
          supposed to do — an agent will try to fix it, and you approve the
          result before anything is saved.
        </p>
        <Link to="/submit">Submit a repair</Link>
      </>
    );
  }

  return (
    <>
      <h1>Queue</h1>
      <ul>
        {repairs.map((r) => (
          <li key={r.id}>
            <Link to={`/repairs/${r.id}`}>
              <strong>{r.status.replace("_", " ")}</strong> — {r.intent}
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}

function Submit() {
  const [intent, setIntent] = useState("");
  const [brokenQuery, setBrokenQuery] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createRepair(intent, brokenQuery);
      navigate("/queue");
    } catch (err) {
      setError((err as Error).message);
      setSubmitting(false);
    }
  }

  return (
    <>
      <h1>Submit a repair</h1>
      <form onSubmit={onSubmit}>
        <div>
          <label htmlFor="intent">What was it supposed to do?</label>
          <input
            id="intent"
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="query">The broken query</label>
          <textarea
            id="query"
            value={brokenQuery}
            onChange={(e) => setBrokenQuery(e.target.value)}
            rows={8}
            required
          />
        </div>
        {error && <p>Couldn't submit: {error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "Submitting…" : "Repair"}
        </button>
      </form>
    </>
  );
}

function Runs() {
  return <h1>Runs</h1>;
}

export default function App() {
  return (
    <BrowserRouter>
      <nav>
        <Link to="/queue">Queue</Link> | <Link to="/runs">Runs</Link> |
        <Link to="/submit">Submit</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Queue />} />
        <Route path="/queue" element={<Queue />} />
        <Route path="/repairs/:id" element={<Repair />} />
        <Route path="/runs" element={<Runs />} />
        <Route path="/submit" element={<Submit />} />
      </Routes>
    </BrowserRouter>
  );
}
