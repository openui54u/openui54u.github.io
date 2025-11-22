export default function StrategyPanel({ symbol }) {
  return (
    <div className="strategy-panel">
      <h2>Trading Strategies for {symbol}</h2>
      <label>
        Moving Average Window:
        <input type="number" defaultValue={14} />
      </label>
      <label>
        Alert Threshold:
        <input type="number" defaultValue={5} />
      </label>
      <button>Apply</button>
    </div>
  );
}
