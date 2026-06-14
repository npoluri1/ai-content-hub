import { Box, Typography, Grid, Card, CardContent, Switch, FormControlLabel, Chip } from '@mui/material';
import NotificationsIcon from '@mui/icons-material/Notifications';

const CHANNELS = [
  { name: 'Email Digest', desc: 'Daily/weekly email summaries', channel: 'email', enabled: true },
  { name: 'Slack Alerts', desc: 'Real-time alerts to Slack', channel: 'slack', enabled: true },
  { name: 'Telegram Bot', desc: 'Instant messages via Telegram', channel: 'telegram', enabled: false },
  { name: 'Discord Webhook', desc: 'Community notifications', channel: 'discord', enabled: false },
  { name: 'Webhook URL', desc: 'Custom HTTP webhook', channel: 'webhook', enabled: true },
  { name: 'SMS (Twilio)', desc: 'Critical alerts via SMS', channel: 'sms', enabled: false },
];

export default function Notifications() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>Notifications</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Configure notification channels and alert preferences</Typography>
      <Grid container spacing={2}>
        {CHANNELS.map(ch => (
          <Grid item xs={12} sm={6} md={4} key={ch.name}>
            <Card>
              <CardContent>
                <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                  <Box><Typography variant="subtitle2" fontWeight={700}>{ch.name}</Typography><Typography variant="caption" color="text.secondary">{ch.desc}</Typography></Box>
                  <FormControlLabel control={<Switch checked={ch.enabled} />} label="" sx={{ m: 0 }} />
                </Box>
                <Chip label={ch.enabled ? 'Active' : 'Disabled'} size="small" color={ch.enabled ? 'success' : 'default'} variant="outlined" sx={{ mt: 1 }} />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
