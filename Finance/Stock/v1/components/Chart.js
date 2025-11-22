import { useEffect, useState } from "react";
import { Chart } from "react-charts";

export default function PriceChart({ symbol }) {
  const [data, setData] = useState([]);

  useEffect(() => {
    async function fetchData() {
      const res = await fetch(`/api/finnhub?symbol=${symbol}`);
      const json = await res.json();
      setData([
        {
          label: symbol,
          data: [{ x: new Date(), y: json.c }] // Close price example
        }
      ]);
    }
    fetchData();
  }, [symbol]);

  const series = {
    type: 'line',
    showPoints: false
  };

  return <Chart data={data} series={series} axes={[
    { primary: true, type: 'time', position: 'bottom' },
    { primary: false, type: 'linear', position: 'left' }
  ]} />;
}
