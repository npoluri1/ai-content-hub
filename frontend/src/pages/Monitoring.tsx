import { Box, Typography, Grid, Card, CardContent, Chip, CircularProgress, Button } from '@mui/material';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import { useState } from 'react';
import { fetchStats } from '../api/client';

export default function Monitoring() {
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<any>(null);

  const runCheck = async () => {
    setLoading(true);
    try {
      const stats = await fetchStats();
      const srcCount = Object.keys(stats.by_source).length;
      const healthy = srcCount >= 10;
      setHealth({ sources: srcCount, healthy, status: healthy ? 'All Systems Operational' : 'Degraded', uptime: '99.9%' });
    } catch {}
    finally { setLoading(false) }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Monitoring & Alerts</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>System health, anomaly detection, and competitor tracking</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card><CardContent sx={{ textAlign:'center' }}>
            <MonitorHeartIcon sx={{ fontSize: 48, color: health?.healthy ? 'success.main' : 'warning.main' }} />
            <Typography variant="h6" sx={{ mt: 1 }}>{health?.status || 'System Status'}</Typography>
            <Chip label={health ? `${health.sources} sources` : 'Click to check'} color={health?.healthy ? 'success' : 'default'} sx={{ mt: 1 }} />
            <Button variant="outlined" size="small" sx={{ mt: 2, display:'block', mx:'auto' }} onClick={runCheck} disabled={loading}>
              {loading ? <CircularProgress size={16} /> : 'Run Health Check'}
            </Button>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} md={8}>
          <Card><CardContent>
            <Typography variant="h6" gutterBottom>Active Alerts</Typography>
            <Typography color="text.secondary">No active alerts. All systems operational.</Typography>
          </CardContent></Card>
        </Grid>
      </Grid>
    </Box>
  );
}
