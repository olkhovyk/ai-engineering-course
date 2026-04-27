export interface Dock {
  id: number;
  code: string;
  dock_type: string;
  status: string;
  created_at: string;
}

export interface Truck {
  id: number;
  license_plate: string;
  carrier_name: string;
  cargo_type: string;
  cargo_volume_pallets: number;
  status: string;
  created_at: string;
}

export interface Staff {
  id: number;
  full_name: string;
  role: string;
  status: string;
  phone: string | null;
  created_at: string;
}

export interface Shift {
  id: number;
  staff_id: number;
  shift_date: string;
  start_time: string;
  end_time: string;
  created_by: string;
  created_at: string;
}

export interface Schedule {
  id: number;
  truck_id: number;
  expected_arrival: string;
  actual_arrival: string | null;
  dock_id: number | null;
  estimated_unload_minutes: number;
  status: string;
  created_at: string;
}

export interface Assignment {
  id: number;
  schedule_entry_id: number;
  staff_id: number;
  dock_id: number;
  role_needed: string;
  assigned_at: string;
  completed_at: string | null;
  assigned_by: string;
}

export interface AgentLog {
  id: number;
  agent_name: string;
  event_type: string;
  severity: string;
  message: string;
  payload: any;
  created_at: string;
}

export interface Notification {
  id: number;
  title: string;
  body: string;
  severity: string;
  is_read: boolean;
  source_agent: string | null;
  created_at: string;
}

export interface DashboardSummary {
  total_trucks_today: number;
  trucks_waiting: number;
  trucks_unloading: number;
  trucks_completed: number;
  docks_total: number;
  docks_occupied: number;
  docks_free: number;
  staff_available: number;
  staff_busy: number;
  staff_off_duty: number;
  loaders_available: number;
  forklift_operators_available: number;
  unread_notifications: number;
  alerts_today: number;
}

export interface TimelineEntry {
  schedule_id: number;
  truck_license_plate: string;
  expected_arrival: string;
  actual_arrival: string | null;
  dock_code: string | null;
  status: string;
  estimated_unload_minutes: number;
}

export interface SimulationClock {
  current_time: string;
}

export interface TickResult {
  current_time: string;
  events: { type: string; schedule_id: number; truck_id: number }[];
  staff_on_shift: number;
}

export interface ScenarioResult {
  ok: boolean;
  scenario: string;
  description: string;
  trucks_scheduled: number;
  simulation_date: string;
  current_time: string;
}
