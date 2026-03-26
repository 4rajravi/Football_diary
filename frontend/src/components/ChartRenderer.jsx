import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts'

const COLORS = ['#16a34a', '#f59e0b', '#3b82f6', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']

export default function ChartRenderer({ config }) {
  if (!config || !config.data) return null

  const { type, title, data, xKey = 'label', yKey = 'value' } = config

  return (
    <div>
      {title && (
        <h3 className="text-sm font-medium text-white/60 mb-3">{title}</h3>
      )}

      {type === 'table' ? (
        <DataTable data={data} />
      ) : type === 'line' ? (
        <LineChartView data={data} xKey={xKey} yKey={yKey} />
      ) : type === 'horizontal_bar' ? (
        <HorizontalBarView data={data} xKey={xKey} yKey={yKey} />
      ) : (
        <BarChartView data={data} xKey={xKey} yKey={yKey} />
      )}
    </div>
  )
}

function BarChartView({ data, xKey, yKey }) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(200, data.length * 30 + 60)}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
        <XAxis
          dataKey={xKey}
          tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
          axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1a2332',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '8px',
            color: '#fff',
            fontSize: '12px',
          }}
        />
        <Bar dataKey={yKey} radius={[4, 4, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function HorizontalBarView({ data, xKey, yKey }) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(200, data.length * 36 + 40)}>
      <BarChart data={data} layout="vertical" margin={{ top: 5, right: 20, left: 80, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey={xKey}
          tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={75}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1a2332',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '8px',
            color: '#fff',
            fontSize: '12px',
          }}
        />
        <Bar dataKey={yKey} radius={[0, 4, 4, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function LineChartView({ data, xKey, yKey }) {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
        <XAxis
          dataKey={xKey}
          tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
          axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1a2332',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '8px',
            color: '#fff',
            fontSize: '12px',
          }}
        />
        <Line
          type="monotone"
          dataKey={yKey}
          stroke="#16a34a"
          strokeWidth={2}
          dot={{ fill: '#16a34a', r: 3 }}
          activeDot={{ r: 5, fill: '#f59e0b' }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

function DataTable({ data }) {
  if (!data.length) return null
  const keys = Object.keys(data[0])

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10">
            {keys.map(k => (
              <th key={k} className="text-left py-2 px-2 text-white/40 text-xs uppercase">
                {k.replace(/_/g, ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} className="border-b border-white/5 hover:bg-white/5">
              {keys.map(k => (
                <td key={k} className="py-2 px-2 text-white/80">
                  {row[k]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
