export default function PaperTradingPage() {
  return (
    <div className="pageShell narrowPage">
      <p className="eyebrow">Mode 03 · Simulated only</p>
      <h1>Paper Trading</h1>
      <div className="phasePlaceholder simulatedPlaceholder">
        <span>SIMULATION</span>
        <h2>No broker adapter or order path exists.</h2>
        <p>
          A later phase may add a paper-only adapter after validation and manual approval gates are
          enforced. This surface cannot place real-money orders.
        </p>
      </div>
    </div>
  );
}

