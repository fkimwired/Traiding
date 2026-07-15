export function SimulationBanner() {
  return (
    <aside className="simulationBanner" aria-label="Simulation notice">
      <span className="simulationFlag" aria-hidden="true">
        SIM
      </span>
      <strong>SIMULATED RESEARCH ENVIRONMENT</strong>
      <span>Paper trading is simulated</span>
      <span>No execution capability</span>
      <span>Not investment advice</span>
    </aside>
  );
}
