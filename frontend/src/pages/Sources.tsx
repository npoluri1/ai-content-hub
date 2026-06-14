import { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  CircularProgress,
  Alert,
  Chip,
  Snackbar,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { getSources, triggerScrape, Source } from '../api/client';

export default function Sources() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [scrapingId, setScrapingId] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState('');

  const load = useCallback(async () => {
    try {
      const data = await getSources();
      setSources(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load sources';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleScrape = async (sourceId: string) => {
    setScrapingId(sourceId);
    try {
      const result = await triggerScrape(sourceId);
      setSnackbar(`${result.message} (${result.new_items} new items)`);
      await load();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Scrape failed';
      setSnackbar(`Error: ${msg}`);
    } finally {
      setScrapingId(null);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Sources
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Last Crawl</TableCell>
              <TableCell align="right">Items</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sources.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography color="text.secondary">No sources configured</Typography>
                </TableCell>
              </TableRow>
            ) : (
              sources.map((source) => (
                <TableRow key={source.id} hover>
                  <TableCell>
                    <Typography fontWeight={600}>{source.name}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={source.status}
                      size="small"
                      color={
                        source.status === 'healthy'
                          ? 'success'
                          : source.status === 'error'
                            ? 'error'
                            : 'warning'
                      }
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    {source.last_crawl
                      ? source.last_crawl
                      : 'Never'}
                  </TableCell>
                  <TableCell align="right">{source.items_count}</TableCell>
                  <TableCell align="center">
                    <Button
                      variant="contained"
                      size="small"
                      startIcon={
                        scrapingId === source.id ? (
                          <CircularProgress size={16} color="inherit" />
                        ) : (
                          <PlayArrowIcon />
                        )
                      }
                      disabled={scrapingId === source.id}
                      onClick={() => handleScrape(source.id)}
                    >
                      {scrapingId === source.id ? 'Scraping...' : 'Scrape Now'}
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Snackbar
        open={!!snackbar}
        autoHideDuration={4000}
        onClose={() => setSnackbar('')}
        message={snackbar}
      />
    </Box>
  );
}
