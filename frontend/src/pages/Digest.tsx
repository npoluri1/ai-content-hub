import { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Paper,
  Link,
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import DownloadIcon from '@mui/icons-material/Download';
import { getDigest } from '../api/client';

export default function Digest() {
  const [digest, setDigest] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState('');
  const [generatedAt, setGeneratedAt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await getDigest();
      setDigest(result.digest);
      setDownloadUrl(result.download_url);
      setGeneratedAt(result.generated_at);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate digest';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Digest
      </Typography>

      <Button
        variant="contained"
        size="large"
        startIcon={
          loading ? <CircularProgress size={20} color="inherit" /> : <AutoAwesomeIcon />
        }
        disabled={loading}
        onClick={handleGenerate}
        sx={{ mb: 3 }}
      >
        {loading ? 'Generating...' : 'Generate Digest'}
      </Button>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {digest && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Generated at: {generatedAt}
            </Typography>
            <Button
              variant="outlined"
              size="small"
              startIcon={<DownloadIcon />}
              component={Link}
              href={downloadUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              Download
            </Button>
          </Box>

          <Paper
            sx={{
              p: 3,
              backgroundColor: 'background.default',
              '& h1, & h2, & h3, & h4': {
                color: 'primary.main',
                mt: 2,
                mb: 1,
              },
              '& ul, & ol': {
                pl: 3,
              },
              '& li': {
                mb: 0.5,
              },
              '& p': {
                mb: 1,
                lineHeight: 1.7,
              },
              '& strong': {
                color: 'secondary.main',
              },
              '& hr': {
                borderColor: 'divider',
                my: 2,
              },
            }}
          >
            {digest.split('\n').map((line, i) => {
              if (line.startsWith('### ')) {
                return (
                  <Typography variant="h6" key={i} gutterBottom>
                    {line.replace('### ', '')}
                  </Typography>
                );
              }
              if (line.startsWith('## ')) {
                return (
                  <Typography variant="h5" key={i} gutterBottom>
                    {line.replace('## ', '')}
                  </Typography>
                );
              }
              if (line.startsWith('# ')) {
                return (
                  <Typography variant="h4" key={i} gutterBottom>
                    {line.replace('# ', '')}
                  </Typography>
                );
              }
              if (line.startsWith('- ')) {
                return (
                  <Typography key={i} sx={{ pl: 2 }}>
                    • {line.replace('- ', '')}
                  </Typography>
                );
              }
              if (line.startsWith('---')) {
                return <Box key={i} sx={{ borderTop: 1, borderColor: 'divider', my: 2 }} />;
              }
              if (line.trim() === '') {
                return <Box key={i} sx={{ height: 8 }} />;
              }
              return (
                <Typography key={i} variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                  {line}
                </Typography>
              );
            })}
          </Paper>
        </Box>
      )}
    </Box>
  );
}
