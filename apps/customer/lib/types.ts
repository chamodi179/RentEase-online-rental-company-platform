export interface Branch {
  id: number;
  name: string;
  address: string;
  city: string;
  phone: string | null;
}

export interface ItemPhoto {
  id: number;
  url: string;
  sort_order: number;
}

export interface Category {
  id: number;
  name: string;
  description: string | null;
}

export interface ItemListing {
  id: number;
  name: string;
  description: string | null;
  base_price_daily: string;
  deposit_amount: string;
  status: string;
  branch: Branch;
  photos: ItemPhoto[];
}

export interface ItemDetail extends ItemListing {
  category: Category | null;
}

export interface BookedRange {
  start_datetime: string;
  end_datetime: string;
}

export interface PriceQuote {
  days: number;
  base_amount: string;
  tax_amount: string;
  deposit_amount: string;
  total_amount: string;
}

export interface Booking {
  id: number;
  booking_reference: string;
  item_id: number;
  status: "pending" | "confirmed" | "active" | "completed" | "cancelled";
  start_datetime: string;
  end_datetime: string;
  base_amount: string;
  tax_amount: string;
  deposit_amount: string;
  total_amount: string;
  created_at: string;
  updated_at: string;
  is_refunded: boolean;
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

export interface BookingDetail extends Booking {
  item: ItemListing;
  branch_pickup: Branch;
  branch_dropoff: Branch;
  payments: Payment[];
}

export interface User {
  id: number;
  full_name: string;
  email: string;
  phone: string | null;
  role: string;
  is_verified: boolean;
  created_at: string;
}
