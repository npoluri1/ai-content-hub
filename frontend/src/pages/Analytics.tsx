import { useEffect, useState } from 'react';
import { Box, Typography, Grid, Card, CardContent, CircularProgress } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { fetchStats } from '../api/client';

export default function Analytics() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats().then(s => {
      const chart = Object.entries(s.by_source).map(([n, v]) => ({ name: n, items: v })).sort((a, b) => b.items - a.items);
      setData(chart);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <Box sx={{ display:'flex', justifyContent:'center', mt:8 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Analytics</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Content performance and source analytics</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Items per Source</Typography>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" stroke="#666" />
                  <YAxis stroke="#666" />
                  <Tooltip contentStyle={{ backgroundColor: 'rgba(0,0,0,0.85)', borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)' }} />
                  <Bar dataKey="items" radius={[4,4,0,0]} fill="url(#colorGrad)" />
                  <defs><linearGradient id="colorGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#60A5FA" stopOpacity={0.8}/><stop offset="100%" stopColor="#60A5FA" stopOpacity={0.2}/></linearGradient></defs>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
