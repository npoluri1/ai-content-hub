import { useState } from 'react';
import { Box, Typography, Grid, Card, CardContent, Button, TextField, Chip, CircularProgress, Divider } from '@mui/material';
import GavelIcon from '@mui/icons-material/Gavel';
import { moderateContent } from '../api/client';

export default function Compliance() {
  const [text, setText] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const check = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const r = await moderateContent(text);
      setResult(r.moderation);
    } catch {}
    finally { setLoading(false) }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Compliance Center</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Content moderation, PII detection, and data governance</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Content Moderation</Typography>
              <TextField fullWidth multiline rows={4} value={text} onChange={e => setText(e.target.value)} placeholder="Paste content to moderate..." />
              <Button variant="contained" sx={{ mt: 2 }} onClick={check} disabled={loading || !text.trim()} startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <GavelIcon />}>Check</Button>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card><CardContent>
            <Typography variant="h6" gutterBottom>Result</Typography>
            <Divider sx={{ mb: 2 }} />
            {result ? (
              <Box>
                <Chip label={result.approved ? '✅ Approved' : '❌ Flagged'} color={result.approved ? 'success' : 'error'} />
                <Typography variant="body2" sx={{ mt: 1 }}>Score: {(result.score * 100).toFixed(0)}%</Typography>
                {result.flags?.map((f: any, i: number) => <Chip key={i} label={`${f.type}: ${f.word}`} size="small" color="warning" sx={{ mt: 0.5, mr: 0.5 }} />)}
              </Box>
            ) : <Typography color="text.secondary">Run a check to see results</Typography>}
          </CardContent></Card>
        </Grid>
      </Grid>
    </Box>
  );
}
