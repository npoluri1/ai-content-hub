import { useState, Fragment, ReactNode } from 'react';
import { Box, Typography, Button, CircularProgress, Alert, Paper, Chip, Divider, Link } from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { getDigest } from '../api/client';

function linkify(text: string): ReactNode {
  const parts = text.split(/(https?:\/\/[^\s]+)/g);
  return parts.map((part, i) => {
    if (part.startsWith('http://') || part.startsWith('https://')) {
      return <Link key={i} href={part} target="_blank" rel="noopener noreferrer" sx={{ wordBreak: 'break-all' }}>{part}</Link>;
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}

function renderLine(line: string, i: number) {
  if (!line.trim()) return <Box key={i} sx={{ height: 8 }} />;
  if (line.startsWith('### ')) return <Typography variant="h6" key={i} gutterBottom>{linkify(line.replace('### ',''))}</Typography>;
  if (line.startsWith('## ')) return <Typography variant="h5" key={i} gutterBottom>{linkify(line.replace('## ',''))}</Typography>;
  if (line.startsWith('# ')) return <Typography variant="h4" key={i} gutterBottom>{linkify(line.replace('# ',''))}</Typography>;
  if (line.startsWith('---')) return <Divider key={i} sx={{ my: 2 }} />;
  if (line.startsWith('- [')) {
    const match = line.match(/- \[(.*?)\] (.*)/);
    if (match) return <Box key={i} sx={{ display:'flex', alignItems:'baseline', gap:1, mb:0.5 }}><Chip label={match[1]} size="small" variant="outlined" sx={{ fontSize:10 }} /><Typography variant="body2">{linkify(match[2])}</Typography></Box>;
  }
  if (line.startsWith('- ')) return <Typography key={i} variant="body2" sx={{ pl: 2, mb: 0.3 }}>{linkify(line.slice(2))}</Typography>;
  return <Typography key={i} variant="body2" sx={{ lineHeight: 1.7 }}>{linkify(line)}</Typography>;
}

export default function Digest() {
  const [digest, setDigest] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    setLoading(true); setError('');
    try {
      const r = await getDigest();
      setDigest(r.digest);
    } catch (e: any) { setError(e.message) }
    finally { setLoading(false) }
  };

  const handleCopy = () => {
    if (digest) { navigator.clipboard.writeText(digest); setCopied(true); setTimeout(() => setCopied(false), 2000) }
  };

  return (
    <Box>
      <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'center', mb: 3 }}>
        <Box>
          <Typography variant="h4">AI Digest</Typography>
          <Typography variant="body2" color="text.secondary">Automatically generated summary of recent relevant content</Typography>
        </Box>
        <Box sx={{ display:'flex', gap: 1 }}>
          {digest && <Button size="small" startIcon={<ContentCopyIcon />} onClick={handleCopy}>{copied ? 'Copied!' : 'Copy'}</Button>}
          <Button variant="contained" size="medium" startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <AutoAwesomeIcon />} disabled={loading} onClick={handleGenerate}>
            {loading ? 'Generating...' : 'Generate Digest'}
          </Button>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {!digest && !loading && (
        <Paper sx={{ textAlign:'center', py: 8 }}>
          <AutoAwesomeIcon sx={{ fontSize: 64, color:'text.disabled', mb: 2 }} />
          <Typography color="text.secondary">Click "Generate Digest" to create a summary</Typography>
        </Paper>
      )}

      {loading && <Box sx={{ display:'flex', justifyContent:'center', my: 8 }}><CircularProgress /></Box>}

      {digest && !loading && (
        <Paper sx={{ p: 3, '& h1': { color:'primary.main', fontSize:'1.5rem', fontWeight:800, mb:1, mt:0 },
          '& h2': { color:'primary.main', fontSize:'1.2rem', fontWeight:700, mt:3, mb:1 },
          '& h3': { fontWeight:600, mt:2, mb:0.5 },
          '& ul': { pl: 3 }, '& li': { mb: 0.8, lineHeight:1.6 }, '& p': { mb: 1, lineHeight:1.7 }, '& strong': { color:'secondary.main' },
        }}>
          {digest.split('\n').map((line, i) => renderLine(line, i))}
        </Paper>
      )}
    </Box>
  );
}
