import { useEffect, useState } from 'react';
import type { ParkPulseData } from '../types';
import {
  mockCongestionSegments,
  mockCorridorSummary,
  mockDrilldowns,
  mockEnforcementPlan,
  mockForecast,
  mockHotspots,
  mockLaneHotspots,
  mockMetrics,
  mockRoadspaceIntelligence,
  mockStations
} from './mockData';

const DATA_BASE = '/data';

async function loadJson<T>(path: string): Promise<T> {
  const response = await fetch(`${DATA_BASE}/${path}`, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Failed to load ${path}`);
  }
  return response.json() as Promise<T>;
}

async function loadOptionalJson<T>(path: string, fallback: T): Promise<T> {
  try {
    return await loadJson<T>(path);
  } catch {
    return fallback;
  }
}

export function useParkPulseData() {
  const [data, setData] = useState<ParkPulseData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [
          metrics,
          enforcementPlan,
          hotspots,
          stationSummary,
          forecastSummary,
          drilldowns,
          laneHotspots,
          roadspaceIntelligence,
          congestionSegments,
          corridorSummary
        ] =
          await Promise.all([
            loadJson<ParkPulseData['metrics']>('metrics.json'),
            loadJson<ParkPulseData['enforcementPlan']>('enforcement_plan.json'),
            loadJson<ParkPulseData['hotspots']>('hotspots.geojson'),
            loadJson<ParkPulseData['stationSummary']>('station_summary.json'),
            loadJson<ParkPulseData['forecastSummary']>('forecast_summary.json'),
            loadJson<ParkPulseData['drilldowns']>('hotspot_drilldown.json'),
            loadOptionalJson<ParkPulseData['laneHotspots']>('lane_hotspots.geojson', { type: 'FeatureCollection', features: [] }),
            loadOptionalJson<ParkPulseData['roadspaceIntelligence']>('roadspace_intelligence.json', []),
            loadOptionalJson<ParkPulseData['congestionSegments']>('congestion_risk_segments.geojson', { type: 'FeatureCollection', features: [] }),
            loadOptionalJson<ParkPulseData['corridorSummary']>('corridor_summary.json', [])
          ]);

        if (!cancelled) {
          setData({
            metrics,
            enforcementPlan,
            hotspots,
            stationSummary,
            forecastSummary,
            drilldowns,
            laneHotspots,
            roadspaceIntelligence,
            congestionSegments,
            corridorSummary,
            usingMockData: false
          });
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setData({
            metrics: mockMetrics,
            enforcementPlan: mockEnforcementPlan,
            hotspots: mockHotspots,
            stationSummary: mockStations,
            forecastSummary: mockForecast,
            drilldowns: mockDrilldowns,
            laneHotspots: mockLaneHotspots,
            roadspaceIntelligence: mockRoadspaceIntelligence,
            congestionSegments: mockCongestionSegments,
            corridorSummary: mockCorridorSummary,
            usingMockData: true
          });
          setError(err instanceof Error ? err.message : 'Using fallback mock data');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { data, loading, error };
}
