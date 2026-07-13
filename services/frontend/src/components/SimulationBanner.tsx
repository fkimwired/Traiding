export function SimulationBanner() {
  return (
    <aside className="simulationBanner" aria-label="Simulation notice">
      <span className="statusDot" aria-hidden="true" />
      <strong>Research only</strong>
      <span>Paper trading is simulated</span>
      <span>Not investment advice</span>
    </aside>
  );
}

