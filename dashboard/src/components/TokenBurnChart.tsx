"use client"

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

const data = [
  { time: "00:00", cost: 0.12 },
  { time: "04:00", cost: 0.34 },
  { time: "08:00", cost: 1.20 },
  { time: "12:00", cost: 2.80 },
  { time: "16:00", cost: 4.50 },
  { time: "20:00", cost: 5.10 },
  { time: "24:00", cost: 6.00 },
]

export function TokenBurnChart() {
  return (
    <Card className="rounded-sm border-border bg-black">
      <CardHeader>
        <CardTitle className="text-sm font-medium tracking-wide uppercase text-muted-foreground">Token Burn Rate</CardTitle>
        <CardDescription className="text-xs">API Cost ($) / Last 24 Hours</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <XAxis 
                dataKey="time" 
                stroke="#333" 
                fontSize={10} 
                tickLine={false} 
                axisLine={false} 
              />
              <YAxis 
                stroke="#333" 
                fontSize={10} 
                tickLine={false} 
                axisLine={false} 
                tickFormatter={(value) => `$${value}`}
              />
              <Tooltip 
                contentStyle={{ backgroundColor: "#111", border: "1px solid #333", borderRadius: "2px" }}
                itemStyle={{ color: "#fff", fontSize: "12px" }}
                labelStyle={{ color: "#888", fontSize: "10px", marginBottom: "4px" }}
              />
              <Line 
                type="monotone" 
                dataKey="cost" 
                stroke="#fff" 
                strokeWidth={2} 
                dot={false}
                activeDot={{ r: 4, fill: "#fff" }} 
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
