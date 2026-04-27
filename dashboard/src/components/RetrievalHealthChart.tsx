"use client"

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

const data = [
  { day: "Mon", score: 0.82 },
  { day: "Tue", score: 0.78 },
  { day: "Wed", score: 0.85 },
  { day: "Thu", score: 0.91 },
  { day: "Fri", score: 0.88 },
  { day: "Sat", score: 0.84 },
  { day: "Sun", score: 0.89 },
]

export function RetrievalHealthChart() {
  return (
    <Card className="rounded-none border-dotted border-2 border-zinc-800 bg-black shadow-none">
      <CardHeader className="pb-2">
        <CardTitle className="text-[10px] font-bold tracking-[0.2em] uppercase text-zinc-500">Retrieval Health</CardTitle>
        <CardDescription className="text-xs text-zinc-400">Avg. Cosine Similarity / Last 7 Days</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[180px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
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
                domain={[0, 1]}
                tickFormatter={(value) => value.toFixed(1)}
              />
              <Tooltip 
                cursor={{ fill: '#111' }}
                contentStyle={{ 
                  backgroundColor: "#000", 
                  border: "1px dotted #444", 
                  borderRadius: "0px",
                  fontSize: "12px"
                }}
                itemStyle={{ color: "#fff" }}
                labelStyle={{ color: "#888", marginBottom: "4px", fontSize: "10px" }}
              />
              <Bar 
                dataKey="score" 
                fill="#ececec" 
                radius={[2, 2, 0, 0]}
                barSize={30}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
