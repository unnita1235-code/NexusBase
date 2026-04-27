"use client"

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

const data = [
  { day: "Mon", cost: 1.20 },
  { day: "Tue", cost: 0.85 },
  { day: "Wed", cost: 2.40 },
  { day: "Thu", cost: 1.10 },
  { day: "Fri", cost: 3.20 },
  { day: "Sat", cost: 0.90 },
  { day: "Sun", cost: 1.50 },
]

export function TokenBurnChart() {
  return (
    <Card className="rounded-none border-dotted border-2 border-zinc-800 bg-black shadow-none">
      <CardHeader className="pb-2">
        <CardTitle className="text-[10px] font-bold tracking-[0.2em] uppercase text-zinc-500">Token Burn Rate</CardTitle>
        <CardDescription className="text-xs text-zinc-400">LLM API Cost ($) / Last 7 Days</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[180px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
              <XAxis 
                dataKey="day" 
                stroke="#444" 
                fontSize={10} 
                tickLine={false} 
                axisLine={false} 
                dy={10}
              />
              <YAxis 
                stroke="#444" 
                fontSize={10} 
                tickLine={false} 
                axisLine={false} 
                tickFormatter={(value) => `$${value}`}
              />
              <Tooltip 
                cursor={{ stroke: '#444', strokeWidth: 1 }}
                contentStyle={{ 
                  backgroundColor: "#000", 
                  border: "1px dotted #444", 
                  borderRadius: "0px",
                  fontSize: "12px"
                }}
                itemStyle={{ color: "#fff" }}
                labelStyle={{ color: "#888", marginBottom: "4px", fontSize: "10px" }}
              />
              <Line 
                type="stepAfter" 
                dataKey="cost" 
                stroke="#ececec" 
                strokeWidth={2} 
                dot={false}
                activeDot={{ r: 4, fill: "#fff", stroke: "#000", strokeWidth: 2 }} 
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
