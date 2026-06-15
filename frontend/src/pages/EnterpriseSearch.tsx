import { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Card, CardContent, TextField, Chip, Grid,
  InputAdornment, IconButton, Menu, MenuItem, Button, FormControl,
  InputLabel, Select, Slider, CircularProgress, Alert,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import FilterListIcon from '@mui/icons-material/FilterList';
import ClearIcon from '@mui/icons-material/Clear';
import SortIcon from '@mui/icons-material/Sort';
import ItemCard from '../components/ItemCard';
import type { ContentItem } from '../api/client';
import { searchItems, fetchStats } from '../api/client';

interface Props {
  onItemClick?: (item: ContentItem) => void;
}

const SOURCE_TYPES = ['news', 'paper', 'video', 'podcast', 'post', 'image'];

export default function EnterpriseSearch({ onItemClick }: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sources, setSources] = useState<string[]>([]);
  const [topics, setTopics] = useState<string[]>([]);

  const [filterSource, setFilterSource] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterTopic, setFilterTopic] = useState('');
  const [dateRange, setDateRange] = useState<number>(90);
  const [sortBy, setSortBy] = useState<'date' | 'relevance'>('date');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    fetchStats().then((s) => {
      setSources(Object.keys(s.by_source).filter(Boolean).sort());
      setTopics(Object.keys(s.by_topic).filter(Boolean).sort());
    }).catch(() => {});
  }, []);

  const doSearch = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    setSearched(true);
    try {
      let items = await searchItems(query, filterSource || undefined, 100);
      if (filterType) items = items.filter(i => i.source_type === filterType);
      if (filterTopic) items = items.filter(i => (i.topics || i.topic || '').includes(filterTopic));
      if (dateRange < 90) {
        const cutoff = new Date();
        cutoff.setDate(cutoff.getDate() - dateRange);
        items = items.filter(i => i.published_at && new Date(i.published_at) >= cutoff);
      }
      if (sortBy === 'date') {
        items.sort((a, b) => new Date(b.published_at || 0).getTime() - new Date(a.published_at || 0).getTime());
      }
      setResults(items);
    } catch (e: any) {
      setError(e?.message || 'Search failed');
    } finally {
      setLoading(false);
    }
  }, [query, filterSource, filterType, filterTopic, dateRange, sortBy]);

  const handleKeyDown = (e: React.KeyboardEvent) => { if (e.key === 'Enter') doSearch(); };

  const clearFilters = () => {
    setFilterSource(''); setFilterType(''); setFilterTopic('');
    setDateRange(90); setSortBy('date');
  };

  const hasFilters = filterSource || filterType || filterTopic || dateRange < 90;

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 800 }}>Enterprise Search</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Advanced faceted search across {sources.length} global sources — AI, Quantum, Robotics, Podcasts, Research & more
      </Typography>

      <Card sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <TextField
            fullWidth
            placeholder="Search all content... Try: quantum computing, robotics, LLM, podcast"
            size="medium"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            sx={{ flex: 1, minWidth: 250 }}
            slotProps={{
              input: {
                startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment>,
                endAdornment: query ? (
                  <IconButton size="small" onClick={() => setQuery('')}><ClearIcon /></IconButton>
                ) : undefined,
              },
            }}
          />
          <Button variant="contained" onClick={doSearch} disabled={loading || !query.trim()} sx={{ height: 40 }}>
            {loading ? <CircularProgress size={20} color="inherit" /> : 'Search'}
          </Button>
          <IconButton onClick={(e) => setAnchorEl(e.currentTarget)} color={hasFilters ? 'primary' : 'default'}>
            <FilterListIcon />
          </IconButton>
        </Box>

        <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)} slotProps={{ paper: { sx: { p: 2, width: 320 } } }}>
          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 700 }}>Faceted Filters</Typography>

          <FormControl fullWidth size="small" sx={{ mb: 1.5 }}>
            <InputLabel>Source</InputLabel>
            <Select value={filterSource} label="Source" onChange={(e) => setFilterSource(e.target.value)}>
              <MenuItem value="">All Sources</MenuItem>
              {sources.map(s => <MenuItem key={s} value={s}>{s}</MenuItem>)}
            </Select>
          </FormControl>

          <FormControl fullWidth size="small" sx={{ mb: 1.5 }}>
            <InputLabel>Content Type</InputLabel>
            <Select value={filterType} label="Content Type" onChange={(e) => setFilterType(e.target.value)}>
              <MenuItem value="">All Types</MenuItem>
              {SOURCE_TYPES.map(t => <MenuItem key={t} value={t}>{t}</MenuItem>)}
            </Select>
          </FormControl>

          <FormControl fullWidth size="small" sx={{ mb: 1.5 }}>
            <InputLabel>Topic</InputLabel>
            <Select value={filterTopic} label="Topic" onChange={(e) => setFilterTopic(e.target.value)}>
              <MenuItem value="">All Topics</MenuItem>
              {topics.map(t => <MenuItem key={t} value={t}>{t}</MenuItem>)}
            </Select>
          </FormControl>

          <Box sx={{ px: 1, mb: 1.5 }}>
            <Typography variant="caption" color="text.secondary">Date Range: {dateRange} days</Typography>
            <Slider value={dateRange} onChange={(_, v) => setDateRange(v as number)} min={1} max={90} size="small" />
          </Box>

          <FormControl fullWidth size="small" sx={{ mb: 1.5 }}>
            <InputLabel>Sort By</InputLabel>
            <Select value={sortBy} label="Sort By" onChange={(e) => setSortBy(e.target.value as any)}>
              <MenuItem value="date">Date (Newest)</MenuItem>
              <MenuItem value="relevance">Relevance</MenuItem>
            </Select>
          </FormControl>

          <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
            {hasFilters && <Button size="small" onClick={clearFilters}>Clear Filters</Button>}
            <Button size="small" variant="contained" onClick={() => { setAnchorEl(null); doSearch(); }}>Apply</Button>
          </Box>
        </Menu>

        {hasFilters && (
          <Box sx={{ display: 'flex', gap: 0.5, mt: 2, flexWrap: 'wrap' }}>
            {filterSource && <Chip label={`Source: ${filterSource}`} size="small" onDelete={() => setFilterSource('')} />}
            {filterType && <Chip label={`Type: ${filterType}`} size="small" onDelete={() => setFilterType('')} />}
            {filterTopic && <Chip label={`Topic: ${filterTopic}`} size="small" onDelete={() => setFilterTopic('')} />}
            {dateRange < 90 && <Chip label={`Last ${dateRange} days`} size="small" onDelete={() => setDateRange(90)} />}
            <Chip label={`Sort: ${sortBy}`} size="small" icon={<SortIcon />} />
            <Chip label="Clear all" size="small" onDelete={clearFilters} variant="outlined" color="primary" />
          </Box>
        )}
      </Card>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {!searched && !loading && (
        <Typography color="text.secondary" sx={{ textAlign: 'center', py: 6 }}>
          <SearchIcon sx={{ fontSize: 48, opacity: 0.3, mb: 1 }} /><br />
          Search across 50+ global sources — AI research, quantum computing, robotics, enterprise tech, podcasts & more
        </Typography>
      )}

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {searched && !loading && results.length === 0 && (
        <Typography color="text.secondary" sx={{ textAlign: 'center', py: 6 }}>
          No results found for "{query}". Try different keywords or remove filters.
        </Typography>
      )}

      {searched && !loading && results.length > 0 && (
        <>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              {results.length} result{results.length !== 1 ? 's' : ''} for "{query}"
            </Typography>
          </Box>
          <Grid container spacing={2}>
            {results.map(item => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={item.id}>
                <ItemCard item={item} onClick={onItemClick} />
              </Grid>
            ))}
          </Grid>
        </>
      )}
    </Box>
  );
}
