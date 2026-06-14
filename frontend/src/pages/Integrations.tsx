import { Box, Typography, Grid, Card, CardContent, Chip, Switch, FormControlLabel, Avatar } from '@mui/material';

const INTEGRATIONS = [
  { name: 'Slack', icon: '💬', color: '#4A154B', desc: 'Send digests and alerts to Slack channels', connected: true },
  { name: 'Teams', icon: '💼', color: '#6264A7', desc: 'Microsoft Teams integration for notifications', connected: false },
  { name: 'Discord', icon: '🎮', color: '#5865F2', desc: 'Discord webhook for community updates', connected: true },
  { name: 'Telegram', icon: '✈️', color: '#0088CC', desc: 'Telegram bot for instant notifications', connected: false },
  { name: 'Jira', icon: '📋', color: '#0052CC', desc: 'Create Jira issues from content items', connected: false },
  { name: 'Notion', icon: '📝', color: '#FFFFFF', desc: 'Sync content to Notion databases', connected: false },
  { name: 'Email', icon: '📧', color: '#EA4335', desc: 'SMTP email digests and newsletters', connected: true },
  { name: 'Webhook', icon: '🔗', color: '#666', desc: 'Custom webhook dispatcher', connected: true },
];

export default function Integrations() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>Integrations</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Connect your stack — 8 available integrations</Typography>
      <Grid container spacing={2}>
        {INTEGRATIONS.map(int => (
          <Grid item xs={12} sm={6} md={4} key={int.name}>
            <Card sx={{ '&:hover': { borderColor: int.color } }}>
              <CardContent>
                <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
                  <Box sx={{ display:'flex', alignItems:'center', gap: 1.5 }}>
                    <Avatar sx={{ bgcolor: int.color }}>{int.icon}</Avatar>
                    <Box><Typography variant="subtitle2" fontWeight={700}>{int.name}</Typography><Typography variant="caption" color="text.secondary">{int.desc}</Typography></Box>
                  </Box>
                  <FormControlLabel control={<Switch checked={int.connected} size="small" />} label="" sx={{ m: 0 }} />
                </Box>
                <Box sx={{ mt: 1 }}><Chip label={int.connected ? 'Connected' : 'Disconnected'} size="small" color={int.connected ? 'success' : 'default'} variant="outlined" /></Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
