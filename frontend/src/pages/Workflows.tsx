import { Box, Typography, Grid, Card, CardContent, Chip, Button, LinearProgress } from '@mui/material';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { useState } from 'react';

const WORKFLOWS = [
  { name: 'Daily Content Digest', status: 'active', runs: 145, lastRun: '2h ago', progress: 100 },
  { name: 'Competitor Monitor', status: 'active', runs: 89, lastRun: '1h ago', progress: 100 },
  { name: 'Weekly Report', status: 'paused', runs: 23, lastRun: '3d ago', progress: 0 },
  { name: 'Compliance Scan', status: 'active', runs: 67, lastRun: '30m ago', progress: 65 },
];

export default function Workflows() {
  const [wf, setWf] = useState(WORKFLOWS);
  return (
    <Box>
      <Typography variant="h4" gutterBottom>Workflow Builder</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Automated pipelines and content processing workflows</Typography>
      <Grid container spacing={2}>
        {wf.map(w => (
          <Grid item xs={12} sm={6} key={w.name}>
            <Card>
              <CardContent>
                <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
                  <Box><Typography variant="subtitle1" fontWeight={700}>{w.name}</Typography><Typography variant="caption" color="text.secondary">Last run: {w.lastRun} • {w.runs} total runs</Typography></Box>
                  <Chip label={w.status} size="small" color={w.status === 'active' ? 'success' : 'default'} variant="outlined" />
                </Box>
                <LinearProgress variant="determinate" value={w.progress} sx={{ mt: 2, height: 4, borderRadius: 2 }} />
                <Button size="small" startIcon={<PlayArrowIcon />} sx={{ mt: 1 }}>Run Now</Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
