import { Box, Typography, Grid, Card, CardContent, Chip, Avatar, AvatarGroup, Button } from '@mui/material';
import GroupIcon from '@mui/icons-material/Group';

const WORKSPACES = [
  { name: 'AI Research', members: 5, items: 128, desc: 'Latest AI/ML papers and news' },
  { name: 'Product Team', members: 8, items: 64, desc: 'Product launches and competitor analysis' },
  { name: 'Engineering', members: 12, items: 96, desc: 'Tech stack and architecture discussions' },
  { name: 'Marketing', members: 4, items: 32, desc: 'Content calendar and campaign tracking' },
];

export default function Collaboration() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>Collaboration</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Workspaces, comments, and shared collections</Typography>
      <Grid container spacing={2}>
        {WORKSPACES.map(ws => (
          <Grid item xs={12} sm={6} key={ws.name}>
            <Card sx={{ cursor:'pointer', '&:hover': { transform:'translateY(-2px)' }, transition:'transform 0.15s' }}>
              <CardContent>
                <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
                  <Box><Typography variant="h6">{ws.name}</Typography><Typography variant="body2" color="text.secondary">{ws.desc}</Typography></Box>
                  <GroupIcon color="primary" />
                </Box>
                <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'center', mt: 2 }}>
                  <AvatarGroup max={4} total={ws.members}>
                    {Array.from({ length: Math.min(ws.members, 4) }).map((_, i) => <Avatar key={i} sx={{ width:28, height:28, fontSize:12 }}>{String.fromCharCode(65 + i)}</Avatar>)}
                  </AvatarGroup>
                  <Box><Chip label={`${ws.items} items`} size="small" /><Chip label={`${ws.members} members`} size="small" variant="outlined" sx={{ ml: 0.5 }} /></Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
