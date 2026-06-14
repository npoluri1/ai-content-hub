import { Box, Typography, Grid, Card, CardContent, Chip, LinearProgress } from '@mui/material';
import CachedIcon from '@mui/icons-material/Cached';

const QUEUE = [
  { job: 'Full-text extraction', status: 'completed', items: '1.2K', time: '2.3s' },
  { job: 'Deduplication', status: 'completed', items: '1.2K', time: '1.8s' },
  { job: 'Classification', status: 'completed', items: '1.2K', time: '4.5s' },
  { job: 'Embedding generation', status: 'completed', items: '1.2K', time: '12.1s' },
  { job: 'Topic modeling', status: 'processing', items: '450', time: '6.2s', progress: 45 },
];

export default function Processing() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>Processing Pipeline</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Content processing jobs, extraction, and enrichment</Typography>
      <Card>
        <CardContent>
          {QUEUE.map(q => (
            <Box key={q.job} sx={{ py: 1.5, borderBottom: '1px solid', borderColor: 'divider', '&:last-child': { borderBottom: 0 } }}>
              <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'center', mb: 0.5 }}>
                <Typography variant="body2" fontWeight={600}>{q.job}</Typography>
                <Box sx={{ display:'flex', gap: 1, alignItems:'center' }}>
                  <Chip label={q.items} size="small" variant="outlined" />
                  <Typography variant="caption" color="text.secondary">{q.time}</Typography>
                  <Chip label={q.status} size="small" color={q.status === 'completed' ? 'success' : 'warning'} />
                </Box>
              </Box>
              {'progress' in q && <LinearProgress variant="determinate" value={q.progress} sx={{ height: 3, borderRadius: 2 }} />}
            </Box>
          ))}
        </CardContent>
      </Card>
    </Box>
  );
}
