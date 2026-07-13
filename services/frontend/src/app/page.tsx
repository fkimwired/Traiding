import Link from "next/link";

import { ApiStatus } from "../components/ApiStatus";
import { navigationItems } from "../components/AppNavigation";

const modeDescriptions = [
  "Capture a source claim without pretending ambiguity is a signal.",
  "Normalize, test, reject, and retain a complete research trail.",
  "Observe approved candidates in a clearly simulated environment.",
  "Inspect gates, audit evidence, approvals, and stop conditions.",
] as const;

export default function HomePage() {
  return (
    <div className="pageShell">
      <section className="hero">
        <div>
          <p className="eyebrow">Phase 1 · Control plane online</p>
          <h1>Research claims.<br />Earn promotion.</h1>
          <p className="heroCopy">
            Fable5 is a research-to-paper-trading platform built to surface leakage,
            fragile costs, and overfitting before a strategy reaches simulation.
          </p>
        </div>
        <div className="heroStatus">
          <ApiStatus />
          <p>Strategy execution is intentionally absent in this phase.</p>
        </div>
      </section>

      <section className="modeGrid" aria-label="Platform modes">
        {navigationItems.map((item, index) => (
          <Link className="modeCard" href={item.href} key={item.href}>
            <span className="modeNumber">0{index + 1}</span>
            <h2>{item.label}</h2>
            <p>{modeDescriptions[index]}</p>
            <span className="cardAction">Open mode →</span>
          </Link>
        ))}
      </section>

      <section className="gateStrip" aria-label="Promotion principles">
        <div>
          <span>01</span>
          <strong>Point-in-time data</strong>
          <p>Availability timestamps, inactive names, and revision history.</p>
        </div>
        <div>
          <span>02</span>
          <strong>Net-of-cost evidence</strong>
          <p>Spread, impact, borrow, latency, capacity, and independent stress vectors.</p>
        </div>
        <div>
          <span>03</span>
          <strong>Selection-aware statistics</strong>
          <p>Complete trial registry, Deflated Sharpe probability, and PBO.</p>
        </div>
      </section>
    </div>
  );
}

