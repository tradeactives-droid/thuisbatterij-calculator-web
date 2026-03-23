/**
 * Types voor BatteryEngine API-responses (frontend referentie; app is vanilla JS).
 */

export type PaybackYears = number | string | null;

export interface RoiTariffEntry {
  yearly_saving_eur?: number;
  roi_percent?: number;
  /** Jaren, null (n.v.t.), of bv. "> 10 jaar" */
  payback_years?: PaybackYears;
}

export interface BatteryApiErrorBody {
  error_code?: string;
  message?: string;
  detail?: string | Array<{ msg?: string }>;
}
