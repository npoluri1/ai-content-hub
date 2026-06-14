import { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Button,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Chip,
  Snackbar,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import { getSources, getSchedule, updateSchedule, Source, ScheduleConfig } from '../api/client';

const INTERVAL_OPTIONS = [
  { value: 3600, label: 'Every hour' },
  { value: 7200, label: 'Every 2 hours' },
  { value: 14400, label: 'Every 4 hours' },
  { value: 21600, label: 'Every 6 hours' },
  { value: 43200, label: 'Every 12 hours' },
  { value: 86400, label: 'Every 24 hours' },
];

export default function Schedule() {
  const [sources, setSources] = useState<Source[]>([]);
  const [config, setConfig] = useState<ScheduleConfig>({
    interval_seconds: 14400,
    sources: [],
    active: false,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [snackbar, setSnackbar] = useState('');

  const load = useCallback(async () => {
    try {
      const [sourcesData, scheduleData] = await Promise.all([
        getSources(),
        getSchedule(),
      ]);
      setSources(sourcesData);
      setConfig(scheduleData);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load schedule';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleIntervalChange = (e: { target: { value: string } }) => {
    setConfig((prev) => ({ ...prev, interval_seconds: Number(e.target.value) }));
  };

  const handleSourceToggle = (sourceId: string) => {
    setConfig((prev) => ({
      ...prev,
      sources: prev.sources.includes(sourceId)
        ? prev.sources.filter((s) => s !== sourceId)
        : [...prev.sources, sourceId],
    }));
  };

  const handleStart = async () => {
    setSaving(true);
    setError('');
    try {
      const updated = await updateSchedule({ ...config, active: true });
      setConfig(updated);
      setSnackbar('Scheduler started');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to start scheduler';
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleStop = async () => {
    setSaving(true);
    setError('');
    try {
      const updated = await updateSchedule({ ...config, active: false });
      setConfig(updated);
      setSnackbar('Scheduler stopped');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to stop scheduler';
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error && sources.length === 0) {
    return <Alert severity="error">{error}</Alert>;
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Schedule
      </Typography>

      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Chip
          label={config.active ? 'Active' : 'Inactive'}
          color={config.active ? 'success' : 'default'}
          variant="outlined"
        />
        <Typography variant="body2" color="text.secondary">
          {config.active ? 'Scheduler is running' : 'Scheduler is stopped'}
        </Typography>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Interval
          </Typography>
          <FormControl size="medium" sx={{ minWidth: 240 }}>
            <InputLabel>Scrape Interval</InputLabel>
            <Select
              value={String(config.interval_seconds)}
              label="Scrape Interval"
              onChange={handleIntervalChange}
            >
              {INTERVAL_OPTIONS.map((opt) => (
                <MenuItem key={opt.value} value={String(opt.value)}>
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Sources
          </Typography>
          <FormGroup>
            {sources.length === 0 ? (
              <Typography color="text.secondary">No sources available</Typography>
            ) : (
              sources.map((source) => (
                <FormControlLabel
                  key={source.id}
                  control={
                    <Checkbox
                      checked={config.sources.includes(source.id)}
                      onChange={() => handleSourceToggle(source.id)}
                    />
                  }
                  label={source.name}
                />
              ))
            )}
          </FormGroup>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button
          variant="contained"
          color="success"
          startIcon={
            saving ? <CircularProgress size={18} color="inherit" /> : <PlayArrowIcon />
          }
          disabled={saving || config.active || config.sources.length === 0}
          onClick={handleStart}
        >
          {saving ? 'Saving...' : 'Start'}
        </Button>
        <Button
          variant="outlined"
          color="error"
          startIcon={<StopIcon />}
          disabled={saving || !config.active}
          onClick={handleStop}
        >
          Stop
        </Button>
      </Box>

      <Snackbar
        open={!!snackbar}
        autoHideDuration={4000}
        onClose={() => setSnackbar('')}
        message={snackbar}
      />
    </Box>
  );
}
