import { useEffect, useState } from 'react';
import {
  Box,
  Grid,
  Typography,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Chip,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import StorageIcon from '@mui/icons-material/Storage';
import RssFeedIcon from '@mui/icons-material/RssFeed';
import TopicIcon from '@mui/icons-material/Topic';
import StatsCard from '../components/StatsCard';
import ItemCard from '../components/ItemCard';
import { fetchStats, getRecent, Stats, ContentItem } from '../api/client';

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recent, setRecent] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const [statsData, recentData] = await Promise.all([fetchStats(), getRecent()]);
        setStats(statsData);
        setRecent(recentData);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to load dashboard';
        setError(msg);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  const topicChartData = stats?.topic_distribution
    ? Object.entries(stats.topic_distribution).map(([name, count]) => ({ name, count }))
    : [];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={4}>
          <StatsCard
            title="Total Items"
            value={stats?.total_items ?? 0}
            icon={<StorageIcon sx={{ fontSize: 40 }} />}
            color="#90caf9"
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <StatsCard
            title="Sources"
            value={stats?.total_sources ?? 0}
            icon={<RssFeedIcon sx={{ fontSize: 40 }} />}
            color="#6cc644"
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <StatsCard
            title="Topics"
            value={stats?.total_topics ?? 0}
            icon={<TopicIcon sx={{ fontSize: 40 }} />}
            color="#f48fb1"
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Topic Distribution
              </Typography>
              {topicChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={topicChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="name" stroke="#999" fontSize={12} />
                    <YAxis stroke="#999" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#132f4c',
                        border: '1px solid #333',
                        borderRadius: 8,
                      }}
                    />
                    <Bar dataKey="count" fill="#90caf9" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Typography color="text.secondary">No topic data available</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Source Health
              </Typography>
              {stats?.source_health ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {Object.entries(stats.source_health).map(([source, status]) => (
                    <Box
                      key={source}
                      sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                    >
                      <Typography variant="body2">{source}</Typography>
                      <Chip
                        label={status}
                        size="small"
                        color={status === 'healthy' ? 'success' : status === 'error' ? 'error' : 'warning'}
                        variant="outlined"
                      />
                    </Box>
                  ))}
                </Box>
              ) : (
                <Typography color="text.secondary">No source health data</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
            Recent Items
          </Typography>
          <Grid container spacing={2}>
            {recent.length > 0 ? (
              recent.slice(0, 6).map((item) => (
                <Grid item xs={12} sm={6} md={4} key={item.id}>
                  <ItemCard item={item} />
                </Grid>
              ))
            ) : (
              <Grid item xs={12}>
                <Typography color="text.secondary">No recent items</Typography>
              </Grid>
            )}
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
}
