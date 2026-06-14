import { useState, useCallback } from 'react';
import {
  Box,
  Typography,
  TextField,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  InputAdornment,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import ItemCard from '../components/ItemCard';
import { searchItems, ContentItem } from '../api/client';

const SOURCES = ['', 'arxiv', 'github', 'medium', 'reddit', 'twitter', 'news', 'blog', 'youtube'];

export default function Search() {
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('');
  const [results, setResults] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);

  const doSearch = useCallback(async (q: string, src: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError('');
    setSearched(true);
    try {
      const data = await searchItems(q.trim(), src || undefined, 50);
      setResults(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Search failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      doSearch(query, source);
    }
  };

  const handleSourceChange = (e: { target: { value: string } }) => {
    const src = e.target.value;
    setSource(src);
    if (query.trim()) {
      doSearch(query, src);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Search
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <TextField
          placeholder="Search content..."
          value={query}
          onChange={handleQueryChange}
          onKeyDown={handleKeyDown}
          size="medium"
          sx={{ flexGrow: 1, minWidth: 280 }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            },
          }}
        />
        <FormControl size="medium" sx={{ minWidth: 160 }}>
          <InputLabel>Source</InputLabel>
          <Select
            value={source}
            label="Source"
            onChange={handleSourceChange}
          >
            <MenuItem value="">All Sources</MenuItem>
            {SOURCES.filter(Boolean).map((s) => (
              <MenuItem key={s} value={s}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {!loading && searched && results.length === 0 && !error && (
        <Typography color="text.secondary">No results found</Typography>
      )}

      <Grid container spacing={2}>
        {results.map((item) => (
          <Grid item xs={12} sm={6} md={4} key={item.id}>
            <ItemCard item={item} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
