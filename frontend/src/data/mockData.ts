import type {
  CongestionSegmentsGeoJson,
  CorridorSummary,
  Drilldown,
  EnforcementPlanRow,
  ForecastSummary,
  LaneHotspotsGeoJson,
  HotspotsGeoJson,
  Metrics,
  RoadspaceHotspot,
  StationSummary
} from '../types';

export const mockEnforcementPlan: EnforcementPlanRow[] = [
  {
    rank: 1,
    zone_id: 'kr_market_09_12',
    zone_name: 'KR Market Area',
    police_station: 'City Market',
    best_time_window: '09-12 Commercial',
    expected_violations: 412,
    expected_impact_score: 96.4,
    final_priority_score: 96.4,
    stable_pcis: 0.91,
    emerging_score: 0.18,
    confidence_band: 'High',
    recommended_action: 'Tow + fixed-window enforcement',
    reasoning: 'Recurring market spillover with main-road no-parking pressure and high auto/car obstruction mix.',
    estimated_patrol_hours: 4,
    estimated_tow_hours: 2,
    enforcement_roi: 8.9,
    estimated_lane_recovery_minutes: 126,
    recovery_minutes_per_resource_hour: 21,
    impact_confidence_note: 'High-confidence recovery opportunity',
    centroid_lat: 12.964,
    centroid_lon: 77.577
  },
  {
    rank: 2,
    zone_id: 'safina_plaza_10_12',
    zone_name: 'Safina Plaza Junction',
    police_station: 'Shivajinagar',
    best_time_window: '09-12 Commercial',
    expected_violations: 365,
    expected_impact_score: 94.7,
    final_priority_score: 94.7,
    stable_pcis: 0.89,
    emerging_score: 0.14,
    confidence_band: 'High',
    recommended_action: 'Fixed-window enforcement',
    reasoning: 'High recurrence around a named junction with strong commercial morning pressure.',
    estimated_patrol_hours: 4,
    estimated_tow_hours: 0,
    enforcement_roi: 9.1,
    estimated_lane_recovery_minutes: 101,
    recovery_minutes_per_resource_hour: 25.3,
    impact_confidence_note: 'Well-supported recovery opportunity',
    centroid_lat: 12.981,
    centroid_lon: 77.61
  },
  {
    rank: 3,
    zone_id: 'hosahalli_metro_08_10',
    zone_name: 'Hosahalli Metro Station Spillover',
    police_station: 'Vijayanagara',
    best_time_window: '06-09 Morning',
    expected_violations: 188,
    expected_impact_score: 89.2,
    final_priority_score: 89.2,
    stable_pcis: 0.82,
    emerging_score: 0.25,
    confidence_band: 'Medium',
    recommended_action: 'Metro/market spillover control',
    reasoning: 'Metro feeder parking pressure with recurring morning concentration.',
    estimated_patrol_hours: 2,
    estimated_tow_hours: 0,
    enforcement_roi: 10.4,
    estimated_lane_recovery_minutes: 68,
    recovery_minutes_per_resource_hour: 34,
    impact_confidence_note: 'Useful but moderate-confidence recovery estimate',
    centroid_lat: 12.974,
    centroid_lon: 77.535
  },
  {
    rank: 4,
    zone_id: 'hal_old_airport_00_06',
    zone_name: 'HAL Old Airport Road',
    police_station: 'HAL Old Airport',
    best_time_window: '00-06 Night',
    expected_violations: 621,
    expected_impact_score: 100,
    final_priority_score: 100,
    stable_pcis: 0.94,
    emerging_score: 0.1,
    confidence_band: 'High',
    recommended_action: 'Engineering fix + targeted patrol',
    reasoning: 'Outer Ring Road hotspot remains important after exposure adjustment and shows heavy vehicle obstruction.',
    estimated_patrol_hours: 4,
    estimated_tow_hours: 0,
    enforcement_roi: 8.7,
    estimated_lane_recovery_minutes: 93,
    recovery_minutes_per_resource_hour: 23.3,
    impact_confidence_note: 'High-confidence recovery opportunity',
    centroid_lat: 12.95,
    centroid_lon: 77.7
  }
];

export const mockHotspots: HotspotsGeoJson = {
  type: 'FeatureCollection',
  features: mockEnforcementPlan.map((row) => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [row.centroid_lon, row.centroid_lat] },
    properties: {
      zone_id: row.zone_id,
      zone_name: row.zone_name,
      police_station: row.police_station,
      centroid_lat: row.centroid_lat,
      centroid_lon: row.centroid_lon,
      tori_score: row.final_priority_score,
      final_priority_score: row.final_priority_score,
      stable_pcis: row.stable_pcis,
      emerging_score: row.emerging_score,
      recommended_action: row.recommended_action,
      confidence_band: row.confidence_band,
      best_time_window: row.best_time_window,
      expected_violations: row.expected_violations,
      expected_impact_score: row.expected_impact_score,
      enforcement_roi: row.enforcement_roi,
      reasoning: row.reasoning
    }
  }))
};

export const mockLaneHotspots: LaneHotspotsGeoJson = {
  type: 'FeatureCollection',
  features: mockEnforcementPlan.map((row) => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [row.centroid_lon, row.centroid_lat] },
    properties: {
      zone_id: row.zone_id,
      zone_name: row.zone_name,
      police_station: row.police_station,
      time_window: row.best_time_window,
      lane_context: row.recommended_action.includes('Metro') ? 'Metro feeder access lane' : 'Main-road kerb lane',
      dominant_lane_issue: row.reasoning,
      lane_obstruction_proxy_0_100: row.final_priority_score,
      lane_obstruction_band: row.final_priority_score >= 90 ? 'Critical' : 'High',
      final_tori_0_100: row.final_priority_score,
      violation_count: row.expected_violations,
      confidence_band: row.confidence_band,
      recommended_action: row.recommended_action,
      mitigation_plan: [
        { phase: 'Peak window', step: row.recommended_action },
        { phase: 'Evidence', step: 'Capture repeat-obstruction photos and vehicle numbers.' }
      ],
      reason_codes: [
        {
          reason: 'Illegal parking obstruction pressure',
          evidence: row.reasoning,
          support_level: 'observed'
        }
      ],
      officer_brief: `${row.police_station}: ${row.reasoning}`,
      historical_workforce_proxy: 'Mock historical enforcement presence',
      signal_health_status: 'External signal-health feed required',
      live_workforce_status: 'External duty roster feed required',
      exact_location_note: 'Mock fallback coordinates'
    }
  }))
};

export const mockRoadspaceIntelligence: RoadspaceHotspot[] = mockLaneHotspots.features.map((feature) => ({
  zone_id: feature.properties.zone_id,
  zone_name_readable: feature.properties.zone_name,
  station: feature.properties.police_station,
  time_window_readable: feature.properties.time_window,
  centroid_lat: feature.geometry.coordinates[1],
  centroid_lon: feature.geometry.coordinates[0],
  lane_context: feature.properties.lane_context,
  dominant_lane_issue: feature.properties.dominant_lane_issue,
  lane_obstruction_proxy_0_100: feature.properties.lane_obstruction_proxy_0_100,
  lane_obstruction_band: feature.properties.lane_obstruction_band,
  final_tori_0_100: feature.properties.final_tori_0_100,
  violation_count: feature.properties.violation_count,
  confidence_band: feature.properties.confidence_band,
  recommended_action: feature.properties.recommended_action,
  historical_workforce_proxy: feature.properties.historical_workforce_proxy,
  signal_health_status: feature.properties.signal_health_status,
  live_workforce_status: feature.properties.live_workforce_status,
  reason_codes: feature.properties.reason_codes,
  mitigation_plan: feature.properties.mitigation_plan,
  officer_brief: feature.properties.officer_brief
}));

const riskColor = (score: number): string => (score >= 90 ? '#D93025' : score >= 75 ? '#F4C430' : '#2874F0');
const riskBand = (score: number): 'low' | 'moderate' | 'severe' =>
  score >= 90 ? 'severe' : score >= 75 ? 'moderate' : 'low';

// A small inferred corridor network so the offline map is populated in fallback mode.
export const mockCongestionSegments: CongestionSegmentsGeoJson = {
  type: 'FeatureCollection',
  features: mockEnforcementPlan.flatMap((row, index) => {
    const [lon, lat] = [row.centroid_lon, row.centroid_lat];
    const score = row.final_priority_score;
    return [0, 1, 2].map((step) => ({
      type: 'Feature' as const,
      geometry: {
        type: 'LineString' as const,
        coordinates: [
          [lon + step * 0.004, lat + step * 0.0025 - index * 0.001],
          [lon + (step + 1) * 0.004, lat + (step + 1) * 0.0025 - index * 0.001]
        ] as [number, number][]
      },
      properties: {
        segment_id: `mock_${index}_${step}`,
        station: row.police_station,
        corridor_name: row.zone_name,
        snap_method: 'data-inferred-corridor-centerline',
        obstruction_score: score,
        risk_band: riskBand(score),
        risk_label: `${riskBand(score)} obstruction risk`,
        color: riskColor(score),
        max_tori: score,
        total_violations: row.expected_violations,
        top_time_window: row.best_time_window,
        lane_context: 'Main-road kerb lane',
        dominant_issue: row.reasoning,
        bottleneck_class: 'Arterial kerb-lane choke',
        recommended_action: row.recommended_action
      }
    }));
  })
};

export const mockCorridorSummary: CorridorSummary[] = mockEnforcementPlan.map((row, index) => ({
  rank: index + 1,
  corridor_id: `${row.police_station}|${row.zone_name}`,
  station: row.police_station,
  corridor_name: row.zone_name,
  linked_hotspots: 4 - Math.min(3, index),
  total_violations: row.expected_violations,
  approx_length_m: 420 - index * 40,
  approx_length_km: Number(((420 - index * 40) / 1000).toFixed(2)),
  max_tori: row.final_priority_score,
  mean_obstruction: row.final_priority_score - 2,
  dominant_bottleneck: 'Arterial kerb-lane choke',
  peak_window: row.best_time_window,
  centroid_lat: row.centroid_lat,
  centroid_lon: row.centroid_lon
}));

export const mockMetrics: Metrics = {
  total_violations: 298450,
  total_hotspots: 10306,
  high_impact_hotspots: 1030,
  predicted_risk_tomorrow: 0.138,
  tow_priority_zones: 35,
  average_confidence: 0.63,
  capture_at_10: 0.081,
  capture_at_20: 0.139,
  raw_count_baseline_capture_at_20: 0.138,
  parkpulse_capture_at_20: 0.139,
  robust_top20_overlap: 0.85,
  headline_recurrence_signal: 'Weighted obstruction density',
  headline_recurrence_capture_at_20: 0.139,
  selected_forecast_model: 'hist_gradient_boosting',
  selected_forecast_capture_at_20: 0.139,
  weighted_obstruction_capture_at_20: 0.139,
  time_safe_historical_capture_at_20: 0.136,
  tori_capture_at_20: 0.037,
  elrm_capture_at_20: 0.021,
  elrm_efficiency_capture_at_20: 0.015,
  capacity_loss_capture_at_20: 0.049,
  spillback_risk_capture_at_20: 0.052,
  operational_priority_capture_at_20: 0.047,
  evidence_quality_capture_at_20: 0.034,
  best_validation_method_at_20: 'Weighted obstruction density',
  best_validation_capture_at_20: 0.139,
  evening_records: 367,
  night_records: 100444,
  evening_to_night_record_ratio: 0.00365,
  evening_window_quality_note: 'The 18-22 window is unusually sparse in the provided records; flag as data coverage risk.',
  judge_positioning: 'Predict recurrence with weighted obstruction/history/model signals; use TORI to explain severity and choose action; use ELRM to compare deployment payoff.',
  top20_lane_recovery_minutes: 388,
  top20_lane_recovery_minutes_low: 310,
  top20_lane_recovery_minutes_high: 458,
  top20_capacity_loss_minutes: 512,
  top20_mean_spillback_risk: 64,
  top20_mean_evidence_quality: 86,
  plan_lane_recovery_minutes: 1640,
  plan_lane_recovery_minutes_low: 1312,
  plan_lane_recovery_minutes_high: 1935,
  plan_capacity_loss_minutes: 2360,
  high_spillback_risk_zones: 18,
  immediate_clearance_zones: 22,
  median_clearance_sla_minutes: 60,
  avg_evidence_quality_score: 78,
  recovery_minutes_per_resource_hour: 24.2,
  best_station_for_recovery: 'HAL Old Airport',
  standard_budget_policy: 'ParkPulse operational priority',
  standard_budget_best_recovery_policy: 'ELRM maximum recovery',
  standard_budget_recovery_minutes: 1180,
  standard_budget_capacity_loss_minutes: 1640,
  standard_budget_high_spillback_zones: 7,
  standard_budget_immediate_clearance_zones: 9,
  standard_budget_recovery_per_resource_hour: 47.2,
  standard_budget_mean_evidence_quality: 91,
  parkpulse_vs_tori_recovery_uplift_pct: 8.4,
  parkpulse_vs_density_recovery_uplift_pct: 13.2,
  policy_lab_note: 'Policy simulation compares dispatch rules under patrol/tow budgets using transparent operational estimates.'
};

export const mockStations: StationSummary[] = [
  {
    police_station: 'HAL Old Airport',
    total_violations: 20819,
    high_impact_hotspots: 74,
    avg_priority_score: 72,
    peak_time_window: '00-06 Night',
    top_action: 'Engineering fix + targeted patrol',
    confidence_band: 'High',
    patrol_hours_required: 26,
    tow_hours_required: 8,
    recoverable_lane_minutes: 402,
    recovery_minutes_per_resource_hour: 24.1
  },
  {
    police_station: 'Shivajinagar',
    total_violations: 28044,
    high_impact_hotspots: 82,
    avg_priority_score: 69,
    peak_time_window: '09-12 Commercial',
    top_action: 'Fixed-window enforcement',
    confidence_band: 'High',
    patrol_hours_required: 31,
    tow_hours_required: 4,
    recoverable_lane_minutes: 377,
    recovery_minutes_per_resource_hour: 21.7
  }
];

export const mockForecast: ForecastSummary[] = mockEnforcementPlan.map((row) => ({
  created_date: '2024-04-08',
  best_time_window: row.best_time_window,
  zone_id: row.zone_id,
  zone_name: row.zone_name,
  police_station: row.police_station,
  predicted_impact_score: row.expected_impact_score,
  predicted_violation_count: row.expected_violations,
  emerging_score: row.emerging_score,
  confidence_band: row.confidence_band
}));

export const mockDrilldowns: Drilldown[] = mockEnforcementPlan.map((row) => ({
  zone_id: row.zone_id,
  zone_name: row.zone_name,
  hourly_pattern: Array.from({ length: 24 }, (_, hour) => ({
    hour,
    value: hour >= 8 && hour <= 12 ? Math.round(row.expected_violations / 8) : Math.round(row.expected_violations / 40)
  })),
  weekday_pattern: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((name, index) => ({
    name,
    value: Math.round(row.expected_violations * (index >= 5 ? 0.18 : 0.12))
  })),
  violation_mix: [
    { name: 'Wrong parking', value: 48 },
    { name: 'No parking', value: 38 },
    { name: 'Main road', value: 14 }
  ],
  vehicle_mix: [
    { name: 'Two-wheeler', value: 42 },
    { name: 'Car', value: 33 },
    { name: 'Auto/Cab', value: 18 },
    { name: 'Goods/Heavy', value: 7 }
  ],
  validation_status_mix: [
    { name: 'Approved', value: 61 },
    { name: 'Pending/created', value: 21 },
    { name: 'Rejected/duplicate', value: 18 }
  ],
  recurrence_trend: Array.from({ length: 20 }, (_, index) => ({
    date: `D-${20 - index}`,
    value: Math.max(0, Math.round(row.expected_violations / 20 + Math.sin(index / 2) * 6))
  })),
  explanation: row.reasoning
}));
