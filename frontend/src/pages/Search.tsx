import { useState, useCallback, useEffect } from 'react';
import {
  Box, Typography, TextField, Grid, FormControl, InputLabel, Select, MenuItem,
  CircularProgress, Alert, InputAdornment, Chip, Paper, IconButton, Slider,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import ClearIcon from '@mui/icons-material/Clear';
import ItemCard from '../components/ItemCard';
import { searchItems, getSources, ContentItem } from '../api/client';

interface Props { onItemClick: (item: ContentItem) => void }

export default function Search({ onItemClick }: Props) {
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('');
  const [limit, setLimit] = useState(20);
  const [results, setResults] = useState<ContentItem[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);

  useEffect(() => { getSources().then(s => setSources(s.map(x => x.name))).catch(() => {}) }, []);

  const doSearch = useCallback(async (q: string, src: string, lim: number) => {
    if (!q.trim()) return;
    setLoading(true); setError(''); setSearched(true);
    try {
      const data = await searchItems(q.trim(), src || undefined, lim);
      const sorted = [...data].sort((a, b) => {
        const da = a.published_at ? new Date(a.published_at).getTime() : 0;
        const db = b.published_at ? new Date(b.published_at).getTime() : 0;
        return db - da;
      });
      setResults(sorted);
    } catch (e: any) { setError(e.message) }
    finally { setLoading(false) }
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') doSearch(query, source, limit);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Enterprise Search</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Search across all ingested content with faceted filtering</Typography>

      <Paper sx={{ p: 2.5, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={5}>
            <TextField
              fullWidth placeholder="Search content, topics, sources..."
              value={query} onChange={e => setQuery(e.target.value)} onKeyDown={handleKeyDown}
              size="small"
              slotProps={{
                input: {
                  startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment>,
                  endAdornment: query ? <InputAdornment position="end"><IconButton size="small" onClick={() => { setQuery(''); setResults([]); setSearched(false) }}><ClearIcon fontSize="small" /></IconButton></InputAdornment> : null,
                },
              }}
            />
          </Grid>
          <Grid item xs={6} md={2.5}>
            <FormControl fullWidth size="small">
              <InputLabel>Source</InputLabel>
              <Select value={source} label="Source" onChange={e => setSource(e.target.value)}>
                <MenuItem value="">All Sources</MenuItem>
                {sources.map(s => <MenuItem key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</MenuItem>)}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={6} md={2.5}>
            <Box sx={{ px: 1 }}>
              <Typography variant="caption" color="text.secondary">Results: {limit}</Typography>
              <Slider value={limit} onChange={(_, v) => setLimit(v as number)} min={5} max={100} step={5} size="small" />
            </Box>
          </Grid>
          <Grid item xs={12} md={2}>
            <Box sx={{ display:'flex', gap:1 }}>
              <IconButton color="primary" onClick={() => doSearch(query, source, limit)} disabled={!query.trim() || loading}>
                {loading ? <CircularProgress size={20} /> : <SearchIcon />}
              </IconButton>
              <Chip label={results.length > 0 ? `${results.length} results` : 'Search'} color={results.length > 0 ? 'primary' : 'default'} size="small" sx={{ alignSelf:'center' }} />
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {loading && <Box sx={{ display:'flex', justifyContent:'center', my:8 }}><CircularProgress /></Box>}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {!loading && searched && results.length === 0 && !error && (
        <Box sx={{ textAlign:'center', py:8 }}>
          <SearchIcon sx={{ fontSize:64, color:'text.disabled', mb:2 }} />
          <Typography color="text.secondary">No results found for "{query}"</Typography>
        </Box>
      )}

      <Grid container spacing={2}>
        {results.map(item => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={item.id}>
            <ItemCard item={item} onClick={onItemClick} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
