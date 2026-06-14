import { useState } from 'react';
import { Box, Typography, Card, CardContent, Grid, Chip, Button, Select, MenuItem, FormControl, InputLabel, Switch, FormControlLabel, Paper, Divider, Slider } from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import ScheduleIcon from '@mui/icons-material/Schedule';
import TimerIcon from '@mui/icons-material/Timer';

const INTERVALS = [
  { value: 3600, label: 'Every hour' },
  { value: 7200, label: 'Every 2 hours' },
  { value: 14400, label: 'Every 4 hours' },
  { value: 21600, label: 'Every 6 hours', default: true },
  { value: 43200, label: 'Every 12 hours' },
  { value: 86400, label: 'Every 24 hours' },
];

const ALL_SOURCES = [
  { id: 'hackernews', name: 'Hacker News', icon: '🔥', active: true },
  { id: 'devto', name: 'Dev.to', icon: '💻', active: true },
  { id: 'medium', name: 'Medium', icon: '📖', active: true },
  { id: 'reddit', name: 'Reddit', icon: '💬', active: true },
  { id: 'arxiv', name: 'ArXiv', icon: '📄', active: true },
  { id: 'youtube', name: 'YouTube', icon: '🎬', active: false },
  { id: 'linkedin', name: 'LinkedIn', icon: '💼', active: false },
  { id: 'techcrunch', name: 'TechCrunch', icon: '📰', active: true },
  { id: 'techgig', name: 'TechGig', icon: '⚡', active: false },
  { id: 'newsapi', name: 'NewsAPI', icon: '📡', active: false },
  { id: 'rss', name: 'RSS Feeds', icon: '📡', active: true },
];

export default function Schedule() {
  const [interval, setInterval] = useState(21600);
  const [active, setActive] = useState(false);
  const [sources, setSources] = useState<string[]>(ALL_SOURCES.filter(s => s.active).map(s => s.id));

  const toggleSource = (id: string) => {
    setSources(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]);
  };

  return (
    <Box>
      <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'center', mb: 3 }}>
        <Box>
          <Typography variant="h4">Scrape Schedule</Typography>
          <Typography variant="body2" color="text.secondary">Configure automated content collection intervals</Typography>
        </Box>
        <Chip label={active ? '● Active' : '○ Inactive'} color={active ? 'success' : 'default'} variant="outlined" />
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display:'flex', alignItems:'center', gap: 1, mb: 2 }}>
                <TimerIcon color="primary" />
                <Typography variant="h6">Interval</Typography>
              </Box>
              <FormControl fullWidth size="small">
                <Select value={interval} onChange={e => setInterval(Number(e.target.value))}>
                  {INTERVALS.map(i => <MenuItem key={i.value} value={i.value}>{i.label}</MenuItem>)}
                </Select>
              </FormControl>
              <Box sx={{ mt: 2 }}>
                <FormControlLabel control={<Switch checked={active} onChange={e => setActive(e.target.checked)} />} label="Enable scheduler" />
              </Box>
            </CardContent>
          </Card>
          <Box sx={{ display:'flex', gap: 1, mt: 2 }}>
            <Button fullWidth variant="contained" color="success" startIcon={<PlayArrowIcon />} disabled={active || sources.length === 0} onClick={() => setActive(true)}>Start</Button>
            <Button fullWidth variant="outlined" color="error" startIcon={<StopIcon />} disabled={!active} onClick={() => setActive(false)}>Stop</Button>
          </Box>
        </Grid>

        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box sx={{ display:'flex', alignItems:'center', gap: 1, mb: 2 }}>
                <ScheduleIcon color="primary" />
                <Typography variant="h6">Sources to Scrape</Typography>
                <Chip label={`${sources.length} selected`} size="small" sx={{ ml: 'auto' }} />
              </Box>
              <Grid container spacing={1}>
                {ALL_SOURCES.map(src => {
                  const sel = sources.includes(src.id);
                  return (
                    <Grid item xs={6} sm={4} key={src.id}>
                      <Paper
                        onClick={() => toggleSource(src.id)}
                        sx={{
                          p: 1.5, cursor: 'pointer', textAlign: 'center', borderRadius: 2,
                          border: sel ? 2 : 1, borderColor: sel ? 'primary.main' : 'divider',
                          bgcolor: sel ? 'action.selected' : 'transparent',
                          transition: 'all 0.15s',
                          '&:hover': { borderColor: 'primary.light' },
                        }}
                      >
                        <Typography variant="h5">{src.icon}</Typography>
                        <Typography variant="caption" fontWeight={600}>{src.name}</Typography>
                      </Paper>
                    </Grid>
                  );
                })}
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Next Scheduled Runs</Typography>
              {active ? (
                <Box sx={{ display:'flex', flexDirection:'column', gap: 1 }}>
                  {sources.slice(0, 5).map(s => {
                    const meta = ALL_SOURCES.find(x => x.id === s);
                    return (
                      <Box key={s} sx={{ display:'flex', alignItems:'center', gap: 2, py: 0.5 }}>
                        <Typography variant="body2">{meta?.icon} {meta?.name}</Typography>
                        <Typography variant="caption" color="text.secondary">Next: {new Date(Date.now() + interval * 1000).toLocaleString()}</Typography>
                        <Box sx={{ flex: 1 }} />
                        <Chip label={`Every ${interval / 3600}h`} size="small" variant="outlined" />
                      </Box>
                    );
                  })}
                </Box>
              ) : (
                <Typography color="text.secondary">Scheduler is stopped. Start it to see upcoming runs.</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
