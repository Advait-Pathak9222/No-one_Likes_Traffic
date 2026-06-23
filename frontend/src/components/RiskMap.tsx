import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import type { CongestionSegmentFeature, CongestionSegmentsGeoJson, HotspotFeature, LaneHotspotFeature } from '../types';
import { oneDecimal } from '../utils/format';

type MapFeature = HotspotFeature | LaneHotspotFeature;
// 'osm' = OpenStreetMap (Leaflet) emergency fallback, used only when the Mappls
// primary basemap fails to initialise. 'unavailable' = both failed.
type BasemapStatus = 'loading' | 'mapmyindia' | 'osm' | 'unavailable';

type ProviderMap = {
  fitBounds?: (bounds: [[number, number], [number, number]] | { bounds: [[number, number], [number, number]] }) => void;
  setCenter?: (center: [number, number] | { lat: number; lng: number }) => void;
  setZoom?: (zoom: number) => void;
  setView?: (center: [number, number] | { lat: number; lng: number }, zoom?: number) => void;
  flyTo?: (options: { center: [number, number] | { lat: number; lng: number }; zoom?: number }) => void;
  remove?: () => void;
};

type SdkWindow = Window & {
  mappls?: { Map?: new (...args: any[]) => ProviderMap };
  MapmyIndia?: { Map?: new (...args: any[]) => ProviderMap };
};

const DEFAULT_MAPMYINDIA_MAP_KEY = 'yxooegymggcadugrvewdohokcacaqhqashdl';
const MAPMYINDIA_MAP_KEY =
  typeof __PARKPULSE_MAPMYINDIA_MAP_KEY__ === 'string' && __PARKPULSE_MAPMYINDIA_MAP_KEY__.trim().length > 0
    ? __PARKPULSE_MAPMYINDIA_MAP_KEY__.trim()
    : DEFAULT_MAPMYINDIA_MAP_KEY;

const MAP_LOG = '[ParkPulse][MapMyIndia]';
const SDK_SCRIPT_ATTR = 'data-parkpulse-mapmyindia-sdk';
const SDK_READY_CALLBACK = '__parkpulseMapplsReady';

type ProviderCtor = new (...args: any[]) => ProviderMap;

function maskKey(key: string): string {
  if (key.length <= 6) return `*** (len ${key.length})`;
  return `${key.slice(0, 3)}…${key.slice(-3)} (len ${key.length})`;
}

// Correct Mappls Web Map SDK endpoint, per the official SDK
// (github.com/mappls-api/mappls-web-maps-js): the static key is the `access_token`
// query param on https://sdk.mappls.com/map/sdk/web — NOT a path segment on the
// legacy apis.mappls.com/advancedmaps/api/<key>/map_sdk endpoint (that one treats
// the path as an OAuth client_id and returns "client does not exist").
//
// The SDK loads its WebGL engine asynchronously and exposes `window.mappls.Map`
// shortly after the script resolves, so we poll for the constructor before
// falling through to the next candidate URL.
function mapMyIndiaSdkCandidates(key: string): string[] {
  const token = encodeURIComponent(key);
  return [
    `https://sdk.mappls.com/map/sdk/web?v=3.0&access_token=${token}`,
    `https://sdk.mappls.com/map/sdk/web?v=3.0&layer=vector&access_token=${token}`
  ];
}

// The place-search/autosuggest plugin (mappls.search) ships in a separate plugins
// bundle that must be loaded after the core SDK. Loaded once, on demand.
let mapplsPluginsPromise: Promise<void> | null = null;
function loadMapplsPlugins(): Promise<void> {
  if (typeof window === 'undefined' || typeof document === 'undefined') return Promise.resolve();
  if ((window as unknown as { mappls?: { search?: unknown } }).mappls?.search) return Promise.resolve();
  if (mapplsPluginsPromise) return mapplsPluginsPromise;
  mapplsPluginsPromise = new Promise((resolve) => {
    const token = encodeURIComponent(MAPMYINDIA_MAP_KEY);
    const script = document.createElement('script');
    script.src = `https://sdk.mappls.com/map/sdk/plugins?v=3.0&libraries=search&access_token=${token}`;
    script.async = true;
    script.onload = () => {
      console.info(`${MAP_LOG} Plugins bundle loaded (search).`);
      resolve();
    };
    script.onerror = (event) => {
      console.warn(`${MAP_LOG} Plugins bundle failed to load.`, event);
      resolve();
    };
    document.head.appendChild(script);
  });
  return mapplsPluginsPromise;
}

function sdkConstructor(): ProviderCtor | null {
  if (typeof window === 'undefined') return null;
  const sdkWindow = window as SdkWindow;
  return (sdkWindow.mappls?.Map ?? sdkWindow.MapmyIndia?.Map ?? null) as ProviderCtor | null;
}

// Module-level singleton: the SDK <script> is injected at most once regardless of
// how many RiskMap instances mount (Command Center + Hotspot Intelligence).
let sdkLoadPromise: Promise<boolean> | null = null;

function loadMapMyIndiaSdk(key: string): Promise<boolean> {
  if (typeof window === 'undefined' || typeof document === 'undefined') return Promise.resolve(false);
  if (sdkConstructor()) {
    console.info(`${MAP_LOG} SDK constructor already present on window; reusing it.`);
    return Promise.resolve(true);
  }
  if (sdkLoadPromise) return sdkLoadPromise;

  sdkLoadPromise = new Promise<boolean>((resolve) => {
    const candidates = mapMyIndiaSdkCandidates(key);
    let index = 0;
    let settled = false;
    let pollTimer: number | undefined;

    const finish = (ok: boolean) => {
      if (settled) return;
      settled = true;
      if (pollTimer !== undefined) window.clearTimeout(pollTimer);
      const w = window as SdkWindow;
      console.info(`${MAP_LOG} SDK load ${ok ? 'SUCCEEDED' : 'FAILED'} (mappls.Map=${Boolean(w.mappls?.Map)}, MapmyIndia.Map=${Boolean(w.MapmyIndia?.Map)}).`);
      resolve(ok);
    };

    const removeScript = (script: HTMLScriptElement) => {
      try { script.parentNode?.removeChild(script); } catch { /* ignore */ }
    };

    // The SDK calls this global once its engine is ready (the `callback=` param).
    (window as unknown as Record<string, () => void>)[SDK_READY_CALLBACK] = () => {
      console.info(`${MAP_LOG} SDK ready-callback fired.`);
      if (sdkConstructor()) finish(true);
    };

    const loadNext = () => {
      if (settled) return;
      if (sdkConstructor()) { finish(true); return; }
      if (index >= candidates.length) {
        console.error(
          `${MAP_LOG} All SDK URLs exhausted — basemap unavailable. If the scripts above returned 200 but no constructor appeared, this is almost certainly a key activation / domain-whitelist problem for host "${window.location.hostname}".`
        );
        finish(false);
        return;
      }
      const url = candidates[index];
      index += 1;
      console.info(`${MAP_LOG} Loading SDK ${index}/${candidates.length}: ${url}`);
      const script = document.createElement('script');
      script.src = url;
      script.async = true;
      script.defer = true;
      script.setAttribute(SDK_SCRIPT_ATTR, String(index));
      let waited = 0;
      const poll = () => {
        if (settled) return;
        if (sdkConstructor()) {
          console.info(`${MAP_LOG} Constructor detected after ${waited}ms (mappls.Map or MapmyIndia.Map).`);
          finish(true);
          return;
        }
        waited += 250;
        if (waited >= 8000) {
          console.warn(`${MAP_LOG} Timed out after 8s waiting for constructor from: ${url}`);
          removeScript(script);
          loadNext();
          return;
        }
        pollTimer = window.setTimeout(poll, 250);
      };
      script.onload = () => {
        console.info(`${MAP_LOG} Script onload OK: ${url} — polling for constructor…`);
        poll();
      };
      script.onerror = (event) => {
        console.error(`${MAP_LOG} Script FAILED to load (network/blocked): ${url}`, event);
        removeScript(script);
        loadNext();
      };
      document.head.appendChild(script);
    };

    loadNext();
  });

  return sdkLoadPromise;
}

interface RiskMapProps {
  segments: CongestionSegmentsGeoJson;
  hotspots: MapFeature[];
  selectedId?: string;
  onSelect: (zoneId: string) => void;
  fallback: ReactNode;
  compact?: boolean;
  focusSelected?: boolean;
  showControls?: boolean;
  initialMinScore?: number;
  maxVisible?: number;
}

interface HotspotView {
  zoneId: string;
  zoneName: string;
  station: string;
  action: string;
  confidence: string;
  score: number;
  tori: number;
  timeWindow: string;
  laneContext: string;
  issue: string;
  bottleneck?: string;
  lon: number;
  lat: number;
}

interface OverlayBounds {
  minLon: number;
  maxLon: number;
  minLat: number;
  maxLat: number;
}

function readHotspot(feature: MapFeature): HotspotView {
  const props = feature.properties as Record<string, unknown>;
  const isLane = 'lane_obstruction_proxy_0_100' in props;
  const num = (value: unknown, fallbackValue = 0): number =>
    typeof value === 'number' && Number.isFinite(value) ? value : fallbackValue;
  const str = (value: unknown, fallbackValue = ''): string =>
    typeof value === 'string' ? value : fallbackValue;
  const [lon, lat] = feature.geometry.coordinates;
  return {
    zoneId: str(props.zone_id),
    zoneName: str(props.zone_name, 'Hotspot'),
    station: str(props.police_station, '—'),
    action: str(props.recommended_action, 'Targeted patrol'),
    confidence: str(props.confidence_band, 'Medium'),
    score: isLane ? num(props.lane_obstruction_proxy_0_100) : num(props.final_priority_score),
    tori: isLane ? num(props.final_tori_0_100) : num(props.final_priority_score),
    timeWindow: isLane ? str(props.time_window) : str(props.best_time_window),
    laneContext: isLane ? str(props.lane_context, 'Hotspot centroid') : 'Hotspot centroid',
    issue: isLane ? str(props.dominant_lane_issue) : str(props.reasoning),
    bottleneck: typeof props.bottleneck_class === 'string' ? props.bottleneck_class : undefined,
    lon,
    lat
  };
}

function hotspotColor(action: string): string {
  const lower = action.toLowerCase();
  if (lower.includes('tow')) return '#fb641b';
  if (lower.includes('engineering')) return '#7c5cff';
  if (lower.includes('metro') || lower.includes('market')) return '#2fb673';
  if (lower.includes('fixed')) return '#2874f0';
  return '#9fb0c7';
}

function segmentWeight(segment: CongestionSegmentFeature): number {
  const score = segment.properties.obstruction_score || 0;
  return Math.max(2.5, Math.min(8.5, 2 + score / 18));
}

function computeOverlayBounds(views: HotspotView[], segments: CongestionSegmentFeature[]): OverlayBounds {
  const coords: Array<[number, number]> = [];
  views.forEach((view) => coords.push([view.lon, view.lat]));
  segments.slice(0, 1200).forEach((feature) => feature.geometry.coordinates.forEach((coord) => coords.push(coord)));
  const valid = coords.filter(([lon, lat]) => Number.isFinite(lon) && Number.isFinite(lat));
  if (valid.length === 0) {
    return { minLon: 77.45, maxLon: 77.75, minLat: 12.84, maxLat: 13.08 };
  }
  const lons = valid.map(([lon]) => lon);
  const lats = valid.map(([, lat]) => lat);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const lonPad = Math.max((maxLon - minLon) * 0.12, 0.012);
  const latPad = Math.max((maxLat - minLat) * 0.12, 0.012);
  return {
    minLon: minLon - lonPad,
    maxLon: maxLon + lonPad,
    minLat: minLat - latPad,
    maxLat: maxLat + latPad
  };
}

function projectToViewBox(lon: number, lat: number, bounds: OverlayBounds): [number, number] {
  const lonSpan = Math.max(bounds.maxLon - bounds.minLon, 0.00001);
  const latSpan = Math.max(bounds.maxLat - bounds.minLat, 0.00001);
  const x = ((lon - bounds.minLon) / lonSpan) * 1000;
  const y = (1 - (lat - bounds.minLat) / latSpan) * 640;
  return [Math.max(-100, Math.min(1100, x)), Math.max(-80, Math.min(720, y))];
}

function estimateZoom(bounds: OverlayBounds, focusSelected: boolean): number {
  if (focusSelected) return 14.2;
  const span = Math.max(bounds.maxLon - bounds.minLon, bounds.maxLat - bounds.minLat);
  if (span < 0.055) return 13.6;
  if (span < 0.12) return 12.6;
  if (span < 0.24) return 11.4;
  return 10.2;
}

function syncProviderToBounds(provider: ProviderMap | null, bounds: OverlayBounds, focusSelected: boolean): void {
  if (!provider) return;
  const map = provider as any;
  const zoom = estimateZoom(bounds, focusSelected);
  // The Mappls vector map is Mapbox-GL based, so bounds/center use [lng, lat] order.
  const sw: [number, number] = [bounds.minLon, bounds.minLat];
  const ne: [number, number] = [bounds.maxLon, bounds.maxLat];
  const centerLngLat: [number, number] = [
    (bounds.minLon + bounds.maxLon) / 2,
    (bounds.minLat + bounds.maxLat) / 2
  ];
  try {
    if (typeof map.fitBounds === 'function') {
      map.fitBounds([sw, ne], { padding: 36, duration: 0 });
      return;
    }
  } catch {
    // Some SDK versions take fitBounds without an options object — retry bare.
    try {
      map.fitBounds([sw, ne]);
      return;
    } catch {
      /* fall through to center/zoom */
    }
  }
  try {
    if (typeof map.setCenter === 'function') map.setCenter(centerLngLat);
    if (typeof map.setZoom === 'function') map.setZoom(zoom);
    if (typeof map.setCenter !== 'function' && typeof map.jumpTo === 'function') {
      map.jumpTo({ center: centerLngLat, zoom });
    }
  } catch (error) {
    if (typeof console !== 'undefined') console.warn(`${MAP_LOG} map sync failed`, error);
  }
}

function useFilteredMapData({
  segments,
  hotspots,
  selectedId,
  focusSelected,
  maxVisible,
  initialMinScore
}: Pick<RiskMapProps, 'segments' | 'hotspots' | 'selectedId' | 'focusSelected' | 'maxVisible' | 'initialMinScore'>) {
  const [station, setStation] = useState('All');
  const [action, setAction] = useState('All');
  const [minScore, setMinScore] = useState(initialMinScore ?? 80);
  const [highConfidenceOnly, setHighConfidenceOnly] = useState(false);
  const [showCorridors, setShowCorridors] = useState(true);

  const views = useMemo(() => hotspots.map(readHotspot), [hotspots]);
  const selectedView = useMemo(
    () => views.find((view) => view.zoneId === selectedId) ?? null,
    [selectedId, views]
  );
  const stations = useMemo(
    () => ['All', ...Array.from(new Set(views.map((view) => view.station))).sort()],
    [views]
  );
  const actions = useMemo(
    () => ['All', ...Array.from(new Set(views.map((view) => view.action))).sort()],
    [views]
  );

  const visible = useMemo(() => {
    const sourceViews =
      focusSelected && selectedView
        ? views.filter((view) => view.station === selectedView.station || view.zoneId === selectedView.zoneId)
        : views;
    const filtered = sourceViews.filter(
      (view) =>
        view.score >= minScore &&
        (station === 'All' || view.station === station) &&
        (action === 'All' || view.action === action) &&
        (!highConfidenceOnly || view.confidence === 'High')
    );
    const sorted = [...filtered].sort((a, b) => b.score - a.score);
    const capped = typeof maxVisible === 'number' ? sorted.slice(0, maxVisible) : sorted;
    if (selectedView && !capped.some((view) => view.zoneId === selectedView.zoneId)) {
      capped.push(selectedView);
    }
    return capped;
  }, [action, focusSelected, highConfidenceOnly, maxVisible, minScore, selectedView, station, views]);

  const corridorFeatures = useMemo(() => {
    if (!showCorridors) return [];
    const stationFilter = focusSelected && selectedView ? selectedView.station : station;
    const filtered = segments.features.filter(
      (feature) => stationFilter === 'All' || feature.properties.station === stationFilter
    );
    // The source GeoJSON is sorted by severity (all 'severe'/red first), so any prefix
    // a renderer slices (native overlay slice(0,1200), SVG/Leaflet slice(0,1600)) would
    // be red-only. Interleave the risk bands by colour (low, moderate, severe) so the
    // drawn prefix always contains blue + yellow + red proportionally.
    const order = ['#2874F0', '#F4C430', '#D93025'];
    const groups = new Map<string, CongestionSegmentFeature[]>();
    filtered.forEach((feature) => {
      const key = feature.properties.color || '#D93025';
      const bucket = groups.get(key);
      if (bucket) bucket.push(feature);
      else groups.set(key, [feature]);
    });
    const buckets = [
      ...order.filter((color) => groups.has(color)),
      ...Array.from(groups.keys()).filter((color) => !order.includes(color))
    ].map((color) => groups.get(color) as CongestionSegmentFeature[]);
    const interleaved: CongestionSegmentFeature[] = [];
    const maxLen = buckets.reduce((max, bucket) => Math.max(max, bucket.length), 0);
    for (let index = 0; index < maxLen; index += 1) {
      buckets.forEach((bucket) => {
        if (index < bucket.length) interleaved.push(bucket[index]);
      });
    }
    return interleaved;
  }, [focusSelected, segments.features, selectedView, showCorridors, station]);

  return {
    action,
    actions,
    corridorFeatures,
    highConfidenceOnly,
    minScore,
    selectedView,
    setAction,
    setHighConfidenceOnly,
    setMinScore,
    setShowCorridors,
    setStation,
    showCorridors,
    station,
    stations,
    visible,
    views
  };
}

// The Mappls web key is domain-whitelisted for `lvh.me` (which resolves to
// 127.0.0.1). If the dashboard is opened on localhost/127.0.0.1, Mappls rejects
// the referer and we fall back to OSM — so offer a one-click jump to the lvh.me URL.
function lvhMeUrl(): string {
  if (typeof window === 'undefined') return 'http://lvh.me:4173/';
  const { protocol, port, pathname, search, hash } = window.location;
  return `${protocol}//lvh.me${port ? `:${port}` : ''}${pathname}${search}${hash}`;
}

function forceOfflineBasemap(): boolean {
  if (typeof window === 'undefined') return false;
  const params = new URLSearchParams(window.location.search);
  return ['offline', 'osm', 'fallback'].includes((params.get('basemap') ?? '').toLowerCase());
}

export function RiskMap(props: RiskMapProps) {
  const {
    segments,
    hotspots,
    selectedId,
    onSelect,
    compact = false,
    focusSelected = false,
    showControls = true,
    initialMinScore = 80,
    maxVisible
  } = props;
  const data = useFilteredMapData({ segments, hotspots, selectedId, focusSelected, maxVisible, initialMinScore });
  const sdkContainerRef = useRef<HTMLDivElement | null>(null);
  const sdkContainerIdRef = useRef(`parkpulse-mapmyindia-${Math.random().toString(36).slice(2)}`);
  const providerMapRef = useRef<ProviderMap | null>(null);
  const [basemapStatus, setBasemapStatus] = useState<BasemapStatus>('loading');
  const [hovered, setHovered] = useState<HotspotView | null>(null);
  const [mapplsLoaded, setMapplsLoaded] = useState(false);
  const [nativeOverlay, setNativeOverlay] = useState(false);
  const [mapplsFail, setMapplsFail] = useState('');
  const mapplsLayersRef = useRef<any[]>([]);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const overlayBounds = useMemo(
    () => computeOverlayBounds(data.visible, data.corridorFeatures),
    [data.visible, data.corridorFeatures]
  );

  useEffect(() => {
    let cancelled = false;
    const host = typeof window !== 'undefined' ? window.location.hostname : 'unknown';
    if (forceOfflineBasemap()) {
      console.info(`${MAP_LOG} Offline/fallback basemap forced by ?basemap=offline; skipping MapMyIndia SDK load.`);
      setBasemapStatus('osm');
      return () => {
        cancelled = true;
        providerMapRef.current?.remove?.();
        providerMapRef.current = null;
      };
    }
    console.info(
      `${MAP_LOG} RiskMap mounting. key=${maskKey(MAPMYINDIA_MAP_KEY)} host="${host}" container="#${sdkContainerIdRef.current}".`
    );

    const initMap = (): boolean => {
      const container = sdkContainerRef.current;
      if (!container || cancelled) return false;
      if (providerMapRef.current) {
        syncProviderToBounds(providerMapRef.current, overlayBounds, focusSelected);
        return true;
      }
      const Ctor = sdkConstructor();
      if (!Ctor) {
        console.warn(`${MAP_LOG} initMap called but no constructor is present on window.`);
        return false;
      }
      const center = {
        lat: (overlayBounds.minLat + overlayBounds.maxLat) / 2,
        lng: (overlayBounds.minLon + overlayBounds.maxLon) / 2
      };
      const zoom = estimateZoom(overlayBounds, focusSelected);
      try {
        let map: ProviderMap;
        try {
          // Documented Mappls Web SDK signature: new mappls.Map(id, { center: {lat,lng}, ... }).
          map = new Ctor(container.id, { center, zoom, zoomControl: true, location: false, clickableIcons: false });
        } catch (primaryError) {
          console.warn(`${MAP_LOG} Primary constructor signature failed; retrying object form.`, primaryError);
          map = new Ctor({ id: container.id, properties: { center, zoom, zoomControl: true } });
        }
        providerMapRef.current = map;
        try {
          // Mappls Web SDK binds events via map.addListener('load', fn)
          // (developer.mappls.com/mapping/map-events). Keep .on as a defensive fallback.
          const listenable = map as {
            addListener?: (event: string, handler: () => void) => void;
            on?: (event: string, handler: () => void) => void;
          };
          const onLoad = () => {
            console.info(`${MAP_LOG} Basemap "load" event fired — tiles rendered.`);
            if (!cancelled) setMapplsLoaded(true);
          };
          if (typeof listenable.addListener === 'function') listenable.addListener('load', onLoad);
          else listenable.on?.('load', onLoad);
          // Fallback: some SDK builds don't emit 'load' — flip the flag shortly after init
          // so the native overlay still draws.
          window.setTimeout(() => { if (!cancelled) setMapplsLoaded(true); }, 2500);
        } catch {
          /* event binding is best-effort; not all SDK builds expose it */
        }
        console.info(`${MAP_LOG} Map initialized successfully on #${container.id}.`);
        if (!cancelled) setBasemapStatus('mapmyindia');
        syncProviderToBounds(map, overlayBounds, focusSelected);
        return true;
      } catch (error) {
        const reason = error && (error as { message?: string }).message ? (error as { message: string }).message : String(error);
        console.error(`${MAP_LOG} Map construction threw — marking basemap unavailable.`, error);
        if (!cancelled) setMapplsFail(reason);
        return false;
      }
    };

    loadMapMyIndiaSdk(MAPMYINDIA_MAP_KEY).then((ready) => {
      if (cancelled) return;
      if (ready && initMap()) return;
      console.warn(
        `${MAP_LOG} Mappls primary basemap unavailable (key/domain-whitelist). Falling back to the OpenStreetMap basemap. To restore Mappls, whitelist "${host}"/"localhost" for this Web Map SDK key.`
      );
      setBasemapStatus('osm');
    });

    return () => {
      cancelled = true;
      providerMapRef.current?.remove?.();
      providerMapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (basemapStatus !== 'mapmyindia') return;
    syncProviderToBounds(providerMapRef.current, overlayBounds, focusSelected);
  }, [basemapStatus, focusSelected, overlayBounds]);

  // Draw ParkPulse corridors + hotspots as NATIVE Mappls layers (Polyline + Marker)
  // so they are geo-anchored to the vector basemap and track pan/zoom. If the SDK
  // overlay API throws or renders nothing, we clear partial layers and keep the SVG
  // overlay (set nativeOverlay=false) so the map never loses its risk layers.
  useEffect(() => {
    if (basemapStatus !== 'mapmyindia' || !mapplsLoaded) return;
    const mappls = (window as unknown as { mappls?: any }).mappls;
    const map = providerMapRef.current as any;
    if (!mappls || !map) return;

    const clearLayers = () => {
      mapplsLayersRef.current.forEach((layer) => {
        try {
          if (typeof mappls.removeLayer === 'function') mappls.removeLayer({ map, layer });
          else layer?.remove?.();
        } catch {
          /* ignore individual removal errors */
        }
      });
      mapplsLayersRef.current = [];
    };

    clearLayers();
    let drewPolys = 0;
    let drewMarkers = 0;

    try {
      data.corridorFeatures.slice(0, 1200).forEach((feature) => {
        const path = feature.geometry.coordinates
          .filter(([lon, lat]) => Number.isFinite(lon) && Number.isFinite(lat))
          .map(([lon, lat]) => ({ lat, lng: lon }));
        if (path.length < 2) return;
        const poly = new mappls.Polyline({
          map,
          path,
          strokeColor: feature.properties.color || '#2874f0',
          strokeWeight: segmentWeight(feature),
          strokeOpacity: 0.9,
          fitbounds: false
        });
        if (poly) {
          mapplsLayersRef.current.push(poly);
          drewPolys += 1;
        }
      });

      data.visible.slice(0, 300).forEach((view) => {
        if (!Number.isFinite(view.lon) || !Number.isFinite(view.lat)) return;
        const selected = view.zoneId === selectedId;
        const size = Math.round(Math.max(12, Math.min(28, 10 + view.score / 6)));
        const marker = new mappls.Marker({
          map,
          position: { lat: view.lat, lng: view.lon },
          fitbounds: false,
          draggable: false,
          html: `<div class="pp-mappls-dot" style="width:${size}px;height:${size}px;background:${hotspotColor(view.action)};border:${selected ? 3 : 2}px solid ${selected ? '#111827' : '#ffffff'}"></div>`
        });
        if (marker) {
          if (typeof marker.addListener === 'function') {
            marker.addListener('click', () => onSelectRef.current(view.zoneId));
          }
          mapplsLayersRef.current.push(marker);
          drewMarkers += 1;
        }
      });
    } catch (error) {
      console.warn(`${MAP_LOG} Native overlay draw failed; keeping the SVG overlay.`, error);
    }

    const ok = drewPolys > 0 && drewMarkers > 0;
    console.info(`${MAP_LOG} Native overlay: ${drewPolys} corridors, ${drewMarkers} hotspots (active=${ok}).`);
    if (!ok) clearLayers();
    setNativeOverlay(ok);
    if (ok) {
      // Frame the now-loaded map to the data extent (correct [lng,lat] order).
      try {
        syncProviderToBounds(map, overlayBounds, focusSelected);
      } catch {
        /* ignore */
      }
    }

    return () => clearLayers();
  }, [basemapStatus, mapplsLoaded, data.corridorFeatures, data.visible, selectedId, overlayBounds, focusSelected]);

  return (
    <div className={`map-shell mapmyindia-primary ${basemapStatus === 'unavailable' ? 'provider-unavailable' : ''} ${compact ? 'compact' : ''} ${showControls ? '' : 'no-controls'}`}>
      {showControls && (
        <MapControls
          actions={data.actions}
          action={data.action}
          highConfidenceOnly={data.highConfidenceOnly}
          minScore={data.minScore}
          setAction={data.setAction}
          setHighConfidenceOnly={data.setHighConfidenceOnly}
          setMinScore={data.setMinScore}
          setShowCorridors={data.setShowCorridors}
          setStation={data.setStation}
          showCorridors={data.showCorridors}
          station={data.station}
          stations={data.stations}
        />
      )}
      <div className="risk-map-frame">
        {basemapStatus === 'osm' ? (
          <LeafletBasemap
            corridorFeatures={data.corridorFeatures}
            visible={data.visible}
            overlayBounds={overlayBounds}
            selectedId={selectedId}
            focusSelected={focusSelected}
            onSelect={onSelect}
            onFail={() => setBasemapStatus('unavailable')}
          />
        ) : basemapStatus === 'unavailable' ? (
          <div className="mapmyindia-unavailable-panel">
            <strong>Basemap unavailable</strong>
            <span>Both the Mappls primary basemap and the OpenStreetMap fallback failed to load (the browser is likely offline or the tile/SDK hosts are blocked). ParkPulse risk layers below are still live from local analysis output.</span>
          </div>
        ) : (
          <div ref={sdkContainerRef} id={sdkContainerIdRef.current} className="mapmyindia-sdk-canvas active" />
        )}
        {basemapStatus !== 'osm' && !nativeOverlay && (
          <ParkPulseSvgOverlay
            corridorFeatures={data.corridorFeatures}
            hovered={hovered}
            onHover={setHovered}
            onSelect={onSelect}
            overlayBounds={overlayBounds}
            selectedId={selectedId}
            visible={data.visible}
          />
        )}
        {basemapStatus === 'mapmyindia' && mapplsLoaded && providerMapRef.current && (
          <MapplsLiveTools map={providerMapRef.current} compact={compact} />
        )}
        <MapLegend providerStatus={basemapStatus} />
        {basemapStatus === 'osm' && typeof window !== 'undefined' && window.location.hostname !== 'lvh.me' && (
          <a className="mappls-host-hint" href={lvhMeUrl()}>
            Showing OpenStreetMap — this host (<b>{window.location.hostname}</b>) isn’t whitelisted for MapMyIndia.
            <span>Click to open on lvh.me for the Mappls basemap →</span>
          </a>
        )}
        {basemapStatus === 'osm' && typeof window !== 'undefined' && window.location.hostname === 'lvh.me' && mapplsFail && (
          <div className="mappls-host-hint warn">
            MapMyIndia loaded but couldn’t start on this device: <b>{mapplsFail}</b>.
            <span>
              {/web\s*gl/i.test(mapplsFail)
                ? 'Open http://lvh.me:4173 in Chrome/Safari with hardware acceleration ON — not the IDE’s built-in preview pane.'
                : 'See the browser console ([ParkPulse][MapMyIndia]) for details.'}
            </span>
          </div>
        )}
        {hovered && basemapStatus !== 'osm' && !nativeOverlay && <MapTooltip hovered={hovered} onSelect={onSelect} />}
      </div>
      <div className="map-footer">
        <span>{data.visible.length} hotspots shown</span>
        <span>{data.corridorFeatures.length} corridor segments</span>
        <span>{basemapStatus === 'osm'
          ? 'OpenStreetMap fallback basemap'
          : basemapStatus === 'unavailable'
            ? 'Basemap unavailable'
            : 'MapMyIndia/Mappls primary map'} · ParkPulse risk layers</span>
      </div>
    </div>
  );
}

function MapControls({
  actions,
  action,
  highConfidenceOnly,
  minScore,
  setAction,
  setHighConfidenceOnly,
  setMinScore,
  setShowCorridors,
  setStation,
  showCorridors,
  station,
  stations
}: {
  actions: string[];
  action: string;
  highConfidenceOnly: boolean;
  minScore: number;
  setAction: (value: string) => void;
  setHighConfidenceOnly: (value: boolean) => void;
  setMinScore: (value: number) => void;
  setShowCorridors: (value: boolean) => void;
  setStation: (value: string) => void;
  showCorridors: boolean;
  station: string;
  stations: string[];
}) {
  return (
    <div className="map-controls">
      <select value={station} onChange={(event) => setStation(event.target.value)} aria-label="Filter by police station">
        {stations.map((item) => <option key={item}>{item}</option>)}
      </select>
      <select value={action} onChange={(event) => setAction(event.target.value)} aria-label="Filter by enforcement action">
        {actions.map((item) => <option key={item}>{item}</option>)}
      </select>
      <label className="map-slider">
        Min obstruction score {minScore}
        <input type="range" min="0" max="100" value={minScore} onChange={(event) => setMinScore(Number(event.target.value))} />
      </label>
      <label className="toggle-pill">
        <input type="checkbox" checked={highConfidenceOnly} onChange={(event) => setHighConfidenceOnly(event.target.checked)} />
        High confidence only
      </label>
      <label className="toggle-pill">
        <input type="checkbox" checked={showCorridors} onChange={(event) => setShowCorridors(event.target.checked)} />
        Corridor risk
      </label>
    </div>
  );
}

function ParkPulseSvgOverlay({
  corridorFeatures,
  hovered,
  onHover,
  onSelect,
  overlayBounds,
  selectedId,
  visible
}: {
  corridorFeatures: CongestionSegmentFeature[];
  hovered: HotspotView | null;
  onHover: (view: HotspotView | null) => void;
  onSelect: (zoneId: string) => void;
  overlayBounds: OverlayBounds;
  selectedId?: string;
  visible: HotspotView[];
}) {
  return (
    <svg className="parkpulse-map-overlay" viewBox="0 0 1000 640" preserveAspectRatio="none" aria-label="ParkPulse hotspot and corridor risk layers">
      <g className="corridor-svg-casing">
        {corridorFeatures.slice(0, 1600).map((feature, index) => {
          const points = feature.geometry.coordinates.map(([lon, lat]) => projectToViewBox(lon, lat, overlayBounds).join(',')).join(' ');
          return (
            <polyline
              key={`case-${feature.properties.segment_id ?? index}`}
              points={points}
              fill="none"
              stroke="#ffffff"
              strokeWidth={segmentWeight(feature) + 3}
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
      </g>
      <g className="corridor-svg-lines">
        {corridorFeatures.slice(0, 1600).map((feature, index) => {
          const points = feature.geometry.coordinates.map(([lon, lat]) => projectToViewBox(lon, lat, overlayBounds).join(',')).join(' ');
          return (
            <polyline
              key={feature.properties.segment_id ?? index}
              points={points}
              fill="none"
              stroke={feature.properties.color || '#2874f0'}
              strokeWidth={segmentWeight(feature)}
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
      </g>
      <g className="hotspot-svg-points">
        {visible.map((view) => {
          const [x, y] = projectToViewBox(view.lon, view.lat, overlayBounds);
          const selected = view.zoneId === selectedId;
          return (
            <circle
              key={view.zoneId}
              cx={x}
              cy={y}
              r={Math.max(5, Math.min(13, 4 + view.score / 10))}
              fill={hotspotColor(view.action)}
              fillOpacity={selected ? 0.96 : 0.84}
              stroke={selected ? '#111827' : '#ffffff'}
              strokeWidth={selected ? 4 : 1.6}
              vectorEffect="non-scaling-stroke"
              tabIndex={0}
              role="button"
              aria-label={`Open ${view.zoneName}`}
              onClick={() => onSelect(view.zoneId)}
              onFocus={() => onHover(view)}
              onBlur={() => onHover(null)}
              onMouseEnter={() => onHover(view)}
              onMouseLeave={() => onHover(null)}
            />
          );
        })}
        {hovered && (() => {
          const [x, y] = projectToViewBox(hovered.lon, hovered.lat, overlayBounds);
          return (
            <circle
              cx={x}
              cy={y}
              r={18}
              fill="rgba(255,255,255,0.08)"
              stroke="#111827"
              strokeWidth={3}
              vectorEffect="non-scaling-stroke"
              pointerEvents="none"
            />
          );
        })()}
      </g>
    </svg>
  );
}

function MapLegend({ providerStatus }: { providerStatus: BasemapStatus }) {
  return (
    <>
      <div className={`map-provider-badge ${providerStatus}`}>
        <strong>{
          providerStatus === 'mapmyindia' ? 'MapMyIndia / Mappls'
            : providerStatus === 'osm' ? 'OpenStreetMap'
            : providerStatus === 'loading' ? 'Loading MapMyIndia'
            : 'Basemap unavailable'
        }</strong>
        <span>{providerStatus === 'osm' ? 'Fallback basemap · ParkPulse layers' : 'ParkPulse risk layers'}</span>
      </div>
      <div className="risk-legend">
        <strong>Inferred corridor obstruction risk</strong>
        <span><i style={{ background: '#2874F0' }} /> Low</span>
        <span><i style={{ background: '#F4C430' }} /> Moderate</span>
        <span><i style={{ background: '#D93025' }} /> Severe</span>
        <small>Inferred from violation coordinates — not live vehicle speed.</small>
      </div>
    </>
  );
}

function MapTooltip({ hovered, onSelect }: { hovered: HotspotView; onSelect: (zoneId: string) => void }) {
  return (
    <div className="risk-map-tooltip">
      <strong>{hovered.zoneName}</strong>
      <span>{hovered.station} · {hovered.laneContext}</span>
      <span>Lane score {oneDecimal(hovered.score)} · TORI {oneDecimal(hovered.tori)}</span>
      {hovered.bottleneck && <span className="risk-tag">{hovered.bottleneck}</span>}
      <span>{hovered.timeWindow} · {hovered.confidence} confidence</span>
      {hovered.issue && <span className="risk-issue">{hovered.issue}</span>}
      <button type="button" onClick={() => onSelect(hovered.zoneId)}>Open brief</button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// OpenStreetMap (Leaflet) emergency fallback basemap.
//
// Loaded from a CDN at runtime — the SAME injection pattern used for the Mappls
// SDK — so the offline esbuild bundle and package.json stay untouched. This path
// is used ONLY when the Mappls (primary) basemap fails. Corridors and hotspots
// are drawn as NATIVE Leaflet layers (not the linear SVG overlay), so they sit
// exactly on the streets and pan/zoom correctly.
// ---------------------------------------------------------------------------
const OSM_LOG = '[ParkPulse][OSM]';
const LEAFLET_JS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
const LEAFLET_CSS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';

let leafletLoadPromise: Promise<any> | null = null;

function loadLeaflet(): Promise<any> {
  if (typeof window === 'undefined' || typeof document === 'undefined') return Promise.resolve(null);
  if ((window as any).L) return Promise.resolve((window as any).L);
  if (leafletLoadPromise) return leafletLoadPromise;

  leafletLoadPromise = new Promise((resolve) => {
    if (!document.querySelector('link[data-parkpulse-leaflet]')) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = LEAFLET_CSS;
      link.setAttribute('data-parkpulse-leaflet', '1');
      document.head.appendChild(link);
    }
    const script = document.createElement('script');
    script.src = LEAFLET_JS;
    script.async = true;
    script.setAttribute('data-parkpulse-leaflet', '1');
    script.onload = () => {
      console.info(`${OSM_LOG} Leaflet loaded from CDN.`);
      resolve((window as any).L ?? null);
    };
    script.onerror = (event) => {
      console.error(`${OSM_LOG} Leaflet failed to load (browser offline or CDN blocked).`, event);
      resolve(null);
    };
    document.head.appendChild(script);
  });
  return leafletLoadPromise;
}

interface LeafletBasemapProps {
  corridorFeatures: CongestionSegmentFeature[];
  visible: HotspotView[];
  overlayBounds: OverlayBounds;
  selectedId?: string;
  focusSelected: boolean;
  onSelect: (zoneId: string) => void;
  onFail: () => void;
}

function LeafletBasemap({
  corridorFeatures,
  visible,
  overlayBounds,
  selectedId,
  focusSelected,
  onSelect,
  onFail
}: LeafletBasemapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const layerRef = useRef<any>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadLeaflet().then((L) => {
      if (cancelled) return;
      if (!L || !containerRef.current) {
        console.error(`${OSM_LOG} Leaflet unavailable — surfacing unavailable notice.`);
        onFail();
        return;
      }
      try {
        const centerLat = (overlayBounds.minLat + overlayBounds.maxLat) / 2;
        const centerLng = (overlayBounds.minLon + overlayBounds.maxLon) / 2;
        const map = L.map(containerRef.current, { zoomControl: true, attributionControl: true });
        map.setView([centerLat, centerLng], estimateZoom(overlayBounds, focusSelected));
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
          maxZoom: 19,
          subdomains: 'abcd',
          attribution: '© OpenStreetMap contributors © CARTO'
        }).addTo(map);
        mapRef.current = map;
        layerRef.current = L.layerGroup().addTo(map);
        // Container is sized by fl/grid CSS after mount; recompute once it settles.
        window.setTimeout(() => {
          try {
            map.invalidateSize();
          } catch {
            /* ignore */
          }
        }, 80);
        console.info(`${OSM_LOG} OpenStreetMap fallback basemap initialised.`);
        setReady(true);
      } catch (error) {
        console.error(`${OSM_LOG} Leaflet init failed.`, error);
        onFail();
      }
    });
    return () => {
      cancelled = true;
      try {
        mapRef.current?.remove?.();
      } catch {
        /* ignore */
      }
      mapRef.current = null;
      layerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Redraw corridor + hotspot layers whenever the filtered data changes.
  useEffect(() => {
    const L = (window as any).L;
    const map = mapRef.current;
    const group = layerRef.current;
    if (!ready || !L || !map || !group) return;
    group.clearLayers();

    corridorFeatures.slice(0, 1600).forEach((feature) => {
      const latlngs = feature.geometry.coordinates
        .filter(([lon, lat]) => Number.isFinite(lon) && Number.isFinite(lat))
        .map(([lon, lat]) => [lat, lon]);
      if (latlngs.length < 2) return;
      L.polyline(latlngs, {
        color: feature.properties.color || '#2874f0',
        weight: segmentWeight(feature),
        opacity: 0.9,
        lineCap: 'round',
        lineJoin: 'round'
      }).addTo(group);
    });

    visible.forEach((view) => {
      if (!Number.isFinite(view.lon) || !Number.isFinite(view.lat)) return;
      const selected = view.zoneId === selectedId;
      const marker = L.circleMarker([view.lat, view.lon], {
        radius: Math.max(5, Math.min(13, 4 + view.score / 10)),
        color: selected ? '#111827' : '#ffffff',
        weight: selected ? 3 : 1.5,
        fillColor: hotspotColor(view.action),
        fillOpacity: selected ? 0.96 : 0.85
      });
      marker.bindTooltip(`${view.zoneName} · ${view.station}`, { direction: 'top' });
      marker.on('click', () => onSelect(view.zoneId));
      marker.addTo(group);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, corridorFeatures, visible, selectedId]);

  // Re-fit the view when the visible extent changes (filter/selection focus).
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    try {
      map.fitBounds(
        [
          [overlayBounds.minLat, overlayBounds.minLon],
          [overlayBounds.maxLat, overlayBounds.maxLon]
        ],
        { padding: [24, 24] }
      );
    } catch {
      /* ignore */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, overlayBounds]);

  return <div ref={containerRef} className="leaflet-basemap" />;
}

// ---------------------------------------------------------------------------
// Live MapMyIndia tools shown only when the Mappls basemap is active:
//  - place search (mappls.search autosuggest) → fly the map to the picked place
//  - satellite / map-view toggle (mappls.setStyle, hybrid style discovered via getStyles)
// Everything is feature-detected and wrapped in try/catch so it can never break
// the core map.
// ---------------------------------------------------------------------------
function MapplsLiveTools({ map, compact }: { map: any; compact?: boolean }) {
  const searchRef = useRef<HTMLInputElement | null>(null);
  const stylesRef = useRef<{ base?: string; hybrid?: string }>({});
  const [satellite, setSatellite] = useState(false);
  const [hasHybrid, setHasHybrid] = useState(true);

  // Load the search plugin (if needed) and bind the Mappls autosuggest box to the input.
  useEffect(() => {
    const input = searchRef.current;
    if (!map || !input) return;
    let cancelled = false;

    const recenter = (dt: any) => {
      const mappls = (window as unknown as { mappls?: any }).mappls;
      const lat = Number(dt.lat ?? dt.latitude);
      const lng = Number(dt.lng ?? dt.lon ?? dt.longitude);
      try {
        if (Number.isFinite(lat) && Number.isFinite(lng)) {
          if (typeof map.flyTo === 'function') map.flyTo({ center: [lng, lat], zoom: 15 });
          else {
            map.setCenter?.([lng, lat]);
            map.setZoom?.(15);
          }
        } else if (dt.eLoc && mappls && typeof mappls.pinMarker === 'function') {
          mappls.pinMarker({ map, pin: dt.eLoc, zoom: 15 });
        }
      } catch {
        /* ignore recenter errors */
      }
    };

    const bind = (): boolean => {
      const mappls = (window as unknown as { mappls?: any }).mappls;
      if (cancelled || !mappls || typeof mappls.search !== 'function') return false;
      try {
        // eslint-disable-next-line no-new
        new mappls.search(input, { region: 'IND', height: 260 }, (data: any) => {
          const dt = Array.isArray(data) ? data[0] : data;
          if (dt) recenter(dt);
        });
        console.info(`${MAP_LOG} Place-search bound to input.`);
        return true;
      } catch (error) {
        console.warn(`${MAP_LOG} Place-search bind failed.`, error);
        return false;
      }
    };

    if (bind()) return;
    // Plugin not present yet — load it, then poll briefly for mappls.search.
    loadMapplsPlugins().then(() => {
      if (cancelled) return;
      let tries = 0;
      const timer = window.setInterval(() => {
        tries += 1;
        if (bind() || tries > 25) window.clearInterval(timer);
      }, 150);
    });

    return () => {
      cancelled = true;
    };
  }, [map]);

  // Discover the base + hybrid/satellite style names once.
  useEffect(() => {
    const mappls = (window as unknown as { mappls?: any }).mappls;
    if (!mappls || typeof mappls.getStyles !== 'function') {
      setHasHybrid(false);
      return;
    }
    try {
      const styles: any[] = mappls.getStyles() || [];
      const find = (re: RegExp) =>
        styles.find((s) => re.test(String(s?.name)) || re.test(String(s?.displayName)))?.name as string | undefined;
      const hybrid = find(/hybrid|satellite|imagery|aerial/i);
      stylesRef.current = {
        hybrid,
        base: find(/standard|grey|gray|day|vector|default/i) || styles[0]?.name
      };
      setHasHybrid(Boolean(hybrid));
      console.info(
        `${MAP_LOG} Available styles: [${styles.map((s) => s?.name).join(', ')}] · hybrid=${hybrid ?? 'none'}`
      );
    } catch (error) {
      setHasHybrid(false);
      console.warn(`${MAP_LOG} getStyles() failed.`, error);
    }
  }, []);

  const toggleSatellite = () => {
    const mappls = (window as unknown as { mappls?: any }).mappls;
    const next = !satellite;
    const target = next ? stylesRef.current.hybrid : stylesRef.current.base;
    if (!target) return;
    try {
      if (typeof map.setStyle === 'function') map.setStyle(target);
      else if (mappls && typeof mappls.setStyle === 'function') mappls.setStyle(target);
      setSatellite(next);
      console.info(`${MAP_LOG} setStyle("${target}").`);
    } catch (error) {
      console.warn(`${MAP_LOG} setStyle failed.`, error);
    }
  };

  return (
    <div className={`mappls-tools ${compact ? 'compact' : ''}`}>
      <input
        ref={searchRef}
        className="mappls-search-input"
        type="text"
        placeholder="Search a place — e.g. Koramangala…"
        aria-label="Search a place on the map"
      />
      {hasHybrid && (
        <button type="button" className={`mappls-style-toggle ${satellite ? 'on' : ''}`} onClick={toggleSatellite}>
          {satellite ? 'Map view' : 'Satellite'}
        </button>
      )}
    </div>
  );
}

export default RiskMap;
