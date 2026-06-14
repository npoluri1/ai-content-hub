import { createContext, useContext, useState, useMemo, ReactNode } from 'react';
import { createTheme, Theme } from '@mui/material/styles';

export interface ThemePreset {
  name: string;
  label: string;
  primary: string;
  secondary: string;
  background: string;
  paper: string;
  gradient: string;
}

const PRESETS: ThemePreset[] = [
  { name: 'ocean', label: 'Ocean Blue', primary: '#60A5FA', secondary: '#F472B6', background: '#0A1628', paper: '#1A2A4A', gradient: 'linear-gradient(135deg, #60A5FA, #F472B6)' },
  { name: 'emerald', label: 'Emerald Green', primary: '#34D399', secondary: '#60A5FA', background: '#0A1A14', paper: '#0F2A22', gradient: 'linear-gradient(135deg, #34D399, #60A5FA)' },
  { name: 'purple', label: 'Royal Purple', primary: '#A78BFA', secondary: '#F472B6', background: '#120A1A', paper: '#1E1430', gradient: 'linear-gradient(135deg, #A78BFA, #F472B6)' },
  { name: 'sunset', label: 'Sunset Orange', primary: '#FB923C', secondary: '#F472B6', background: '#1A100A', paper: '#2A1A10', gradient: 'linear-gradient(135deg, #FB923C, #F472B6)' },
  { name: 'rose', label: 'Rose Pink', primary: '#FB7185', secondary: '#A78BFA', background: '#1A0A12', paper: '#2A1020', gradient: 'linear-gradient(135deg, #FB7185, #A78BFA)' },
  { name: 'slate', label: 'Slate Gray', primary: '#94A3B8', secondary: '#60A5FA', background: '#0F1215', paper: '#1A1D23', gradient: 'linear-gradient(135deg, #94A3B8, #60A5FA)' },
  { name: 'teal', label: 'Teal Cyan', primary: '#2DD4BF', secondary: '#A78BFA', background: '#081A1A', paper: '#0F2A28', gradient: 'linear-gradient(135deg, #2DD4BF, #A78BFA)' },
  { name: 'amber', label: 'Amber Glow', primary: '#FBBF24', secondary: '#FB923C', background: '#1A1408', paper: '#2A2008', gradient: 'linear-gradient(135deg, #FBBF24, #FB923C)' },
  { name: 'indigo', label: 'Indigo Storm', primary: '#818CF8', secondary: '#34D399', background: '#0A0A1A', paper: '#14142A', gradient: 'linear-gradient(135deg, #818CF8, #34D399)' },
  { name: 'crimson', label: 'Crimson Red', primary: '#F87171', secondary: '#FBBF24', background: '#1A0A0A', paper: '#2A1010', gradient: 'linear-gradient(135deg, #F87171, #FBBF24)' },
];

interface ThemeCtx {
  preset: ThemePreset;
  presets: ThemePreset[];
  theme: Theme;
  setPreset: (name: string) => void;
}

const ThemeContext = createContext<ThemeCtx>(null!);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preset, setPresetState] = useState<ThemePreset>(() => {
    const saved = localStorage.getItem('ai-hub-theme');
    return PRESETS.find(p => p.name === saved) || PRESETS[0];
  });

  const setPreset = (name: string) => {
    const next = PRESETS.find(p => p.name === name) || PRESETS[0];
    setPresetState(next);
    localStorage.setItem('ai-hub-theme', next.name);
  };

  const theme = useMemo(() => createTheme({
    palette: {
      mode: 'dark',
      primary: { main: preset.primary },
      secondary: { main: preset.secondary },
      background: { default: preset.background, paper: preset.paper },
    },
    typography: {
      fontFamily: '"Inter","Segoe UI","Roboto","Helvetica",sans-serif',
      h4: { fontWeight: 800, letterSpacing: '-0.02em' },
      h5: { fontWeight: 700, letterSpacing: '-0.01em' },
      h6: { fontWeight: 700 },
      button: { textTransform: 'none', fontWeight: 600 },
    },
    shape: { borderRadius: 12 },
    components: {
      MuiCard: { styleOverrides: { root: { backgroundImage: 'none', backdropFilter: 'blur(8px)', border: '1px solid', borderColor: 'rgba(255,255,255,0.06)' } } },
      MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
      MuiButton: { styleOverrides: { root: { borderRadius: 8, padding: '8px 20px' } } },
      MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
      MuiDrawer: { styleOverrides: { paper: { borderRight: '1px solid', borderColor: 'rgba(255,255,255,0.06)' } } },
    },
  }), [preset]);

  return (
    <ThemeContext.Provider value={{ preset, presets: PRESETS, theme, setPreset }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useThemePreset = () => useContext(ThemeContext);
