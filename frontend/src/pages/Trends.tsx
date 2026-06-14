import { Box, Typography, Grid, Card, CardContent, Chip } from '@mui/material';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';

const TRENDS = [
  { topic: 'AgenticAI', change: '+28%', direction: 'up', color: '#34D399' },
  { topic: 'RAG', change: '+15%', direction: 'up', color: '#60A5FA' },
  { topic: 'MCP', change: '+42%', direction: 'up', color: '#A78BFA' },
  { topic: 'LLM_Ops', change: '+12%', direction: 'up', color: '#FB923C' },
  { topic: 'Quantum_Computing', change: '+8%', direction: 'up', color: '#F472B6' },
];

export default function Trends() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>Content Trends</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Trending topics and sentiment over time</Typography>
      <Grid container spacing={2}>
        {TRENDS.map(t => (
          <Grid item xs={12} sm={6} md={4} key={t.topic}>
            <Card>
              <CardContent sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box><Typography variant="subtitle1" fontWeight={700}>{t.topic}</Typography><Typography variant="caption" color="text.secondary">Last 7 days</Typography></Box>
                <Chip icon={<ArrowUpwardIcon />} label={t.change} sx={{ bgcolor: `${t.color}22`, color: t.color, fontWeight: 700 }} />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
