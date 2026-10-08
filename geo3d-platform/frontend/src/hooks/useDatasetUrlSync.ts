import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAppStore } from '../stores'

export function useDatasetUrlSync() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { datasets, activeDataset, selectDataset } = useAppStore()

  useEffect(() => {
    const dsId = searchParams.get('dataset')
    if (dsId) {
      if (!activeDataset || activeDataset.id !== dsId) {
        const found = datasets.find((d) => d.id === dsId)
        if (found) {
          selectDataset(found)
        }
      }
    } else if (activeDataset) {
      // Keep search params in sync with current active dataset
      setSearchParams({ dataset: activeDataset.id }, { replace: true })
    }
  }, [searchParams, datasets, activeDataset])

  return { activeDataset }
}
