import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { getModels, switchModel as apiSwitchModel, switchTier as apiSwitchTier, ModelInfo, ModelListResponse } from '../api/client';

interface ModelContextValue {
  activeModel: ModelInfo | null;
  activeTier: string;
  freeModels: ModelInfo[];
  premiumModels: ModelInfo[];
  loading: boolean;
  error: string | null;
  switchToModel: (id: string) => Promise<void>;
  switchToTier: (tier: string) => Promise<void>;
  refresh: () => void;
  globalModelId: string;
  setGlobalModelId: (id: string) => void;
}

const ModelContext = createContext<ModelContextValue>({
  activeModel: null, activeTier: 'premium',
  freeModels: [], premiumModels: [],
  loading: false, error: null,
  switchToModel: async () => {}, switchToTier: async () => {},
  refresh: () => {},
  globalModelId: '', setGlobalModelId: () => {},
});

export function ModelProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<ModelListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const storedGlobal = typeof window !== 'undefined' ? localStorage.getItem('globalModelId') || '' : '';
  const [globalModelId, setGlobalModelId] = useState(storedGlobal);

  const fetchModels = useCallback(async () => {
    try {
      setLoading(true);
      const d = await getModels();
      setData(d);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchModels() }, [fetchModels]);

  const switchToModel = async (id: string) => {
    await apiSwitchModel(id);
    await fetchModels();
  };

  const switchToTier = async (tier: string) => {
    await apiSwitchTier(tier);
    await fetchModels();
  };

  const handleSetGlobalModelId = (id: string) => {
    setGlobalModelId(id);
    localStorage.setItem('globalModelId', id);
  };

  return (
    <ModelContext.Provider value={{
      activeModel: data?.active_model ?? null,
      activeTier: data?.active_tier ?? 'free',
      freeModels: data?.free_models ?? [],
      premiumModels: data?.premium_models ?? [],
      loading, error,
      switchToModel, switchToTier,
      refresh: fetchModels,
      globalModelId, setGlobalModelId: handleSetGlobalModelId,
    }}>
      {children}
    </ModelContext.Provider>
  );
}

export const useModels = () => useContext(ModelContext);
