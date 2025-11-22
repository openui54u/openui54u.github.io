import { useState } from "react";
import Chart from "../components/Chart";
import StrategyPanel from "../components/StrategyPanel";
import SymbolSearch from "../components/SymbolSearch";

export default function Dashboard() {
  const [symbol, setSymbol] = useState("AAPL");

  return (
    <div>
      <h1>Advanced Market Analyst</h1>
      <SymbolSearch setSymbol={setSymbol} />
      <Chart symbol={symbol} />
      <StrategyPanel symbol={symbol} />
    </div>
  );
}
