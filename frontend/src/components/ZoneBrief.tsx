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

export function ZoneBrief({ plan, roadspace }: ZoneBriefProps) {
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

      <div className="brief-metrics officer">
        <div><span>Action</span><strong>{officerActionText(plan.recommended_action)}</strong></div>
        <div><span>When</span><strong>{plan.best_time_window}</strong></div>
        <div><span>Urgency</span><strong>{urgencyText(plan)}</strong></div>
        <div><span>Resource needed</span><strong>{resourceText(plan)}</strong></div>
        <div><span>Main reason</span><strong>{roadspace?.dominant_lane_issue ?? plan.reasoning}</strong></div>
        <div><span>Expected benefit</span><strong>{recoveryRange(plan)}</strong></div>
      </div>

      {roadspace && (
        <section className="brief-section">
          <h3>Road-space read</h3>
          <p><strong>Lane context:</strong> {roadspace.lane_context}</p>
          <p><strong>Dominant issue:</strong> {roadspace.dominant_lane_issue}</p>
          {roadspace.junction_sensitivity_label && <p><strong>Junction sensitivity:</strong> {roadspace.junction_sensitivity_label}</p>}
          {roadspace.corridor_name && (
            <p>
              <strong>Corridor:</strong> part of {roadspace.corridor_name}
              {roadspace.corridor_linked_hotspots ? ` — ${roadspace.corridor_linked_hotspots} linked hotspots` : ''}
              {roadspace.corridor_length_km ? `, ~${oneDecimal(roadspace.corridor_length_km)} km` : ''}
            </p>
          )}
          {plan.violation_text_severity_signature && (
            <p><strong>Violation severity signature:</strong> {plan.violation_text_severity_signature}</p>
          )}
          <p><strong>Confidence note:</strong> {plan.time_window_coverage_warning ?? `${plan.confidence_band} confidence field brief.`}</p>
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
