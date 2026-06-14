import { useEffect, useState } from 'react';
import { Box, Grid, Typography, Card, CardContent, CircularProgress, Alert, Chip } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import StorageIcon from '@mui/icons-material/Storage';
import RssFeedIcon from '@mui/icons-material/RssFeed';
import TopicIcon from '@mui/icons-material/Topic';
import ScheduleIcon from '@mui/icons-material/Schedule';
import StatsCard from '../components/StatsCard';
import ItemCard from '../components/ItemCard';
import { fetchStats, getRecent, getSources, Stats, ContentItem } from '../api/client';

interface Props { onItemClick: (item: ContentItem) => void }

const PIE_COLORS = ['#60A5FA','#34D399','#A78BFA','#FB923C','#FB7185','#FBBF24','#818CF8','#F87171','#2DD4BF','#F472B6'];

export default function Dashboard({ onItemClick }: Props) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recent, setRecent] = useState<ContentItem[]>([]);
  const [sources, setSources] = useState<{name:string;count:number}[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const [s, r, src] = await Promise.all([fetchStats(), getRecent(20), getSources()]);
        setStats(s); setRecent(r); setSources(src);
      } catch (e: any) { setError(e.message) }
      finally { setLoading(false) }
    })();
  }, []);

  if (loading) return <Box sx={{ display:'flex', justifyContent:'center', mt:8 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">{error}</Alert>;

  const topicData = stats?.by_topic ? Object.entries(stats.by_topic).filter(([k]) => k).map(([n, v]) => ({ name: n, value: v })).sort((a, b) => b.value - a.value) : [];
  const totalTopics = topicData.length;
  const topSources = sources.slice(0, 5);

  return (
    <Box>
      <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'center', mb:3 }}>
        <Box>
          <Typography variant="h4">Dashboard</Typography>
          <Typography variant="body2" color="text.secondary">Enterprise content intelligence overview</Typography>
        </Box>
        <Chip label={`Last updated: ${new Date().toLocaleTimeString()}`} size="small" variant="outlined" />
      </Box>

      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard title="Total Items" value={stats?.total_items ?? 0} icon={<StorageIcon sx={{ fontSize:36 }} />} color="#60A5FA" subtitle="Across all sources" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard title="Active Sources" value={sources.length} icon={<RssFeedIcon sx={{ fontSize:36 }} />} color="#34D399" subtitle={`${topSources[0]?.name || ''}${topSources[1] ? `, ${topSources[1]?.name}` : ''}${sources.length > 2 ? '...' : ''}`} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard title="Topics Covered" value={totalTopics} icon={<TopicIcon sx={{ fontSize:36 }} />} color="#A78BFA" subtitle={topicData.slice(0,3).map(t => t.name).join(', ')} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard title="Last Crawl" value={recent[0]?.published_at ? new Date(recent[0].published_at).toLocaleDateString() : 'N/A'} icon={<ScheduleIcon sx={{ fontSize:36 }} />} color="#FB923C" subtitle="Most recent item" />
        </Grid>
      </Grid>

      <Grid container spacing={2.5}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Topic Distribution</Typography>
              {topicData.length > 0 ? (
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={topicData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis type="number" stroke="#666" fontSize={12} />
                    <YAxis dataKey="name" type="category" stroke="#666" fontSize={11} width={120} />
                    <Tooltip contentStyle={{ backgroundColor: 'rgba(0,0,0,0.85)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                    <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                      {topicData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : <Typography color="text.secondary">No topic data</Typography>}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Source Breakdown</Typography>
              {sources.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={sources} dataKey="count" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                      {sources.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: 'rgba(0,0,0,0.85)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : <Typography color="text.secondary">No source data</Typography>}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'center', mb:2, mt: 1 }}>
            <Typography variant="h6">Recent Items</Typography>
            <Chip label={`${recent.length} items`} size="small" />
          </Box>
          <Grid container spacing={2}>
            {recent.slice(0, 8).map(item => (
              <Grid item xs={12} sm={6} md={3} key={item.id}>
                <ItemCard item={item} onClick={onItemClick} />
              </Grid>
            ))}
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
}
