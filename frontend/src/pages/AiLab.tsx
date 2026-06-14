import { useState } from 'react';
import { Box, Typography, Grid, Card, CardContent, TextField, Button, CircularProgress, Chip, Divider } from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { analyzeSentiment, detectPII } from '../api/client';

export default function AiLab() {
  const [text, setText] = useState('');
  const [sentiment, setSentiment] = useState<any>(null);
  const [pii, setPii] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const analyze = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const [s, p] = await Promise.all([analyzeSentiment(text), detectPII(text)]);
      setSentiment(s?.sentiment); setPii(p?.pii_detected);
    } catch {}
    finally { setLoading(false) }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>AI Lab</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>AI-powered content analysis tools</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <TextField fullWidth multiline rows={6} value={text} onChange={e => setText(e.target.value)} placeholder="Paste content to analyze..." variant="outlined" />
              <Button variant="contained" sx={{ mt: 2 }} onClick={analyze} disabled={loading || !text.trim()} startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <SmartToyIcon />}>Analyze</Button>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Results</Typography>
              <Divider sx={{ mb: 2 }} />
              {sentiment && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="overline" color="text.secondary">Sentiment</Typography>
                  <Chip label={sentiment.sentiment} color={sentiment.sentiment === 'positive' ? 'success' : sentiment.sentiment === 'negative' ? 'error' : 'warning'} sx={{ display:'block', mt: 0.5 }} />
                  <Typography variant="body2" sx={{ mt: 0.5 }}>Score: {(sentiment.score * 100).toFixed(0)}%</Typography>
                </Box>
              )}
              {pii && pii.length > 0 && (
                <Box>
                  <Typography variant="overline" color="text.secondary">PII Detected</Typography>
                  {pii.map((p: any, i: number) => <Chip key={i} label={`${p.type}: ${p.value}`} size="small" color="warning" sx={{ display:'block', mt: 0.5 }} />)}
                </Box>
              )}
              {!sentiment && !pii && <Typography color="text.secondary" variant="body2">Run analysis to see results</Typography>}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
