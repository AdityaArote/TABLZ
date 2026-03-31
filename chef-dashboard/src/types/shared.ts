/* TABLZ Shared Types */

export interface Restaurant {
  id: string;
  name: string;
  subscription_tier: "free" | "premium" | "vip" | "luxury";
  currency: string;
}

export interface MenuItem {
  id: string;
  name: string;
  description: string;
  price: number;
  category: string;
  is_available: boolean;
  image_url?: string;
}

export interface Table {
  id: string;
  table_number: number;
  status: "available" | "occupied" | "cleaning";
  max_capacity: number;
}

export interface Order {
  id: string;
  table_id: string;
  status: "pending" | "received" | "preparing" | "ready" | "served" | "cancelled";
  total_amount: number;
  placed_at: string;
  items: OrderItem[];
}

export interface OrderItem {
  id: string;
  menu_item_id: string;
  quantity: number;
  unit_price_at_order: number;
  item_notes?: string;
}
