import { Box, Typography, Grid, Card, CardContent, Chip, CircularProgress, Button } from '@mui/material';
import ScienceIcon from '@mui/icons-material/Science';
import { useState } from 'react';
import { fetchStats } from '../api/client';

export default function MlopsLab() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const runQualityCheck = async () => {
    setLoading(true);
    try {
      const stats = await fetchStats();
      const total = stats.total_items;
      const topics = Object.keys(stats.by_topic).length;
      setResult({ total_items: total, total_topics: topics, quality_score: Math.min(100, Math.round((total / 300) * 100)), status: 'healthy' });
    } catch {}
    finally { setLoading(false) }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>MLOps Lab</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Model operations, quality scoring, and content metrics</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card><CardContent>
            <Typography variant="h6" gutterBottom>Content Quality Score</Typography>
            <Button variant="contained" onClick={runQualityCheck} disabled={loading} startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <ScienceIcon />}>
              {loading ? 'Analyzing...' : 'Run Quality Check'}
            </Button>
            {result && (
              <Box sx={{ mt: 2 }}>
                <Chip label={`Score: ${result.quality_score}/100`} color={result.quality_score > 70 ? 'success' : 'warning'} />
                <Chip label={`Items: ${result.total_items}`} sx={{ ml: 1 }} />
                <Chip label={`Topics: ${result.total_topics}`} sx={{ ml: 1 }} />
              </Box>
            )}
          </CardContent></Card>
        </Grid>
      </Grid>
    </Box>
  );
}
