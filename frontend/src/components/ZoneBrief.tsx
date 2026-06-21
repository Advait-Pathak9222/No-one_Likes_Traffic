import { Printer } from 'lucide-react';
import type { EnforcementPlanRow, RoadspaceHotspot } from '../types';
import { compactNumber, oneDecimal } from '../utils/format';

interface ZoneBriefProps {
  plan: EnforcementPlanRow;
  roadspace?: RoadspaceHotspot;
}

function recoveryRange(plan: EnforcementPlanRow): string {
  const expected = plan.estimated_lane_recovery_minutes;
  const low = plan.estimated_lane_recovery_minutes_low;
  const high = plan.estimated_lane_recovery_minutes_high;
  if (expected === undefined || expected === null) return '—';
  if (low !== undefined && high !== undefined) {
    return `${oneDecimal(expected)} min (range ${oneDecimal(low)}–${oneDecimal(high)})`;
  }
  return `${oneDecimal(expected)} min`;
}

function officerActionText(action: string): string {
  const lower = action.toLowerCase();
  if (lower.includes('tow')) return 'Send tow support and clear parked vehicles';
  if (lower.includes('engineering')) return 'Send patrol and flag for engineering fix';
  if (lower.includes('fixed')) return 'Place a fixed-window enforcement unit';
  if (lower.includes('metro') || lower.includes('market')) return 'Control pickup/drop and spillover parking';
  if (lower.includes('watch')) return 'Keep on watchlist and audit if pressure rises';
  return 'Send targeted patrol';
}

function resourceText(plan: EnforcementPlanRow): string {
  const patrol = plan.estimated_patrol_hours ?? 0;
  const tow = plan.estimated_tow_hours ?? 0;
  if (tow > 0 && patrol > 0) return `Tow + patrol support (${oneDecimal(patrol)} patrol hr, ${oneDecimal(tow)} tow hr)`;
  if (tow > 0) return `Tow support (${oneDecimal(tow)} tow hr)`;
  if (patrol > 0) return `Patrol support (${oneDecimal(patrol)} patrol hr)`;
  return 'Officer audit / watchlist';
}

function urgencyText(plan: EnforcementPlanRow): string {
  const sla = plan.clearance_sla_minutes;
  if (sla === undefined || sla === null) return plan.clearance_decision_band ?? 'Act in target window';
  if (sla <= 30) return `Immediate: within ${compactNumber(sla)} min`;
  if (sla <= 90) return `Same shift: within ${compactNumber(sla)} min`;
  return `Planned: within ${compactNumber(sla)} min`;
}

function reasonPoints(text?: string, limit = 4): string[] {
  if (!text) return [];
  return text
    .split(';')
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, limit);
}

export function ZoneBrief({ plan, roadspace }: ZoneBriefProps) {
  const proofPoints = reasonPoints(plan.reasoning);
  return (
    <article className="zone-brief" id="print-root">
      <header className="brief-header">
        <div>
          <span className="brief-eyebrow">ParkPulse Field Brief · Bengaluru Traffic Police</span>
          <h2>{plan.zone_name}</h2>
          <p>{plan.police_station} · {plan.best_time_window} · Priority rank #{plan.rank}</p>
        </div>
        <button type="button" className="no-print brief-print" onClick={() => window.print()}>
          <Printer size={16} /> Print brief
        </button>
      </header>

      <div className="brief-chips">
        <span className="brief-chip action">{officerActionText(plan.recommended_action)}</span>
        <span className="brief-chip">{plan.confidence_band} confidence</span>
        {plan.hotspot_persistence_class && <span className="brief-chip">{plan.hotspot_persistence_class}</span>}
        {roadspace?.bottleneck_class && <span className="brief-chip">{roadspace.bottleneck_class}</span>}
      </div>

      <ol className="field-order">
        <li>
          <span>Go to</span>
          <strong>{plan.zone_name}</strong>
          <small>{plan.police_station} · centroid {oneDecimal(plan.centroid_lat)}, {oneDecimal(plan.centroid_lon)}</small>
        </li>
        <li>
          <span>Act during</span>
          <strong>{plan.best_time_window}</strong>
          <small>{urgencyText(plan)}</small>
        </li>
        <li>
          <span>Use</span>
          <strong>{resourceText(plan)}</strong>
          <small>{officerActionText(plan.recommended_action)}</small>
        </li>
        <li>
          <span>Why</span>
          <strong>{roadspace?.dominant_lane_issue ?? proofPoints[0] ?? 'Recurring illegal-parking pressure'}</strong>
          <small>{plan.confidence_band} confidence · expected benefit {recoveryRange(plan)}</small>
        </li>
      </ol>

      {roadspace && (
        <section className="brief-section">
          <h3>Road-space proof</h3>
          <ul className="brief-list compact-proof">
            <li><strong>Lane context</strong><span>{roadspace.lane_context}</span></li>
            <li><strong>Dominant issue</strong><span>{roadspace.dominant_lane_issue}</span></li>
            {roadspace.junction_sensitivity_label && (
              <li><strong>Junction sensitivity</strong><span>{roadspace.junction_sensitivity_label}</span></li>
            )}
            {roadspace.corridor_name && (
              <li>
                <strong>Corridor</strong>
                <span>
                  {roadspace.corridor_name}
                  {roadspace.corridor_linked_hotspots ? ` · ${roadspace.corridor_linked_hotspots} linked hotspots` : ''}
                  {roadspace.corridor_length_km ? ` · ~${oneDecimal(roadspace.corridor_length_km)} km` : ''}
                </span>
              </li>
            )}
            <li>
              <strong>Evidence note</strong>
              <span>{plan.time_window_coverage_warning ?? `${plan.confidence_band} confidence field brief.`}</span>
            </li>
          </ul>
        </section>
      )}

      {roadspace && roadspace.reason_codes?.length > 0 && (
        <section className="brief-section">
          <h3>Why this zone matters</h3>
          <ul className="brief-list">
            {roadspace.reason_codes.slice(0, 4).map((reason, index) => (
              <li key={index}>
                <strong>{reason.reason}</strong> <em>({reason.support_level})</em>
                <span>{reason.evidence}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="brief-section">
        <h3>Field action plan</h3>
        {roadspace && roadspace.mitigation_plan?.length > 0 ? (
          <ol className="brief-steps">
            {roadspace.mitigation_plan.map((step, index) => (
              <li key={index}><strong>{step.phase}:</strong> {step.step}</li>
            ))}
          </ol>
        ) : (
          <p>{plan.reasoning}</p>
        )}
      </section>

      <footer className="brief-footer">
        <span>Centroid {oneDecimal(plan.centroid_lat)}, {oneDecimal(plan.centroid_lon)} (from violation coordinates)</span>
        <span>
          Modelled estimates derived only from the enforcement violation dataset. Not live vehicle speed,
          surveyed lane GIS, signal-health telemetry, or live workforce data.
        </span>
      </footer>
    </article>
  );
}

export default ZoneBrief;
