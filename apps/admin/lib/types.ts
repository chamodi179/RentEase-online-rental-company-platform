export interface User {
  id: number;
  full_name: string;
  email: string;
  phone: string | null;
  role: string;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
}

export interface DashboardSummary {
  todays_pickups: number;
  todays_returns: number;
  active_rentals: number;
}

export interface Category {
  id: number;
  name: string;
  description: string | null;
}

export interface ItemPhoto {
  id: number;
  url: string;
  sort_order: number;
}

export interface AdminCatalog {
  id: number;
  category_id: number;
  category: Category | null;
  photos: ItemPhoto[];
}

export interface AdminItem {
  id: number;
  name: string;
  description: string | null;
  base_price_daily: string;
  deposit_amount: string;
  status: "available" | "rented" | "maintenance" | "retired";
  branch_id: number;
  catalog_id: number;
}

export interface AdminBooking {
  id: number;
  booking_reference: string;
  customer_id: number;
  item_id: number;
  status: "pending" | "confirmed" | "active" | "completed" | "cancelled";
  start_datetime: string;
  end_datetime: string;
  total_amount: string;
  created_at: string;
}

export interface BookingDetail extends AdminBooking {
  base_amount: string;
  tax_amount: string;
  deposit_amount: string;
  item: { id: number; name: string };
  branch_pickup: { id: number; name: string; city: string };
  branch_dropoff: { id: number; name: string; city: string };
}

export interface Customer extends User {
  booking_count: number;
}

export interface Payment {
  id: number;
  booking_id: number;
  type: "payment" | "refund";
  amount: string;
  method: "card" | "cash" | "bank_transfer";
  status: "pending" | "success" | "failed";
  created_at: string;
}
