export default function PaperTradingPage() {
  return (
    <div className="pageShell narrowPage">
      <p className="eyebrow">Mode 03 · Simulated only</p>
      <h1>Paper Trading</h1>
      <div className="phasePlaceholder simulatedPlaceholder">
        <span>SIMULATION</span>
        <h2>No broker adapter or order path exists.</h2>
        <p>
          This surface may display historical synthetic approval status only. It cannot submit,
          execute, or fill anything, cannot place real-money orders, and is not investment advice.
        </p>
      </div>
    </div>
  );
}
