# TABLZ Phase 4 Implementation Plan: Chef Dashboard

## Goal
Implement the Chef Dashboard frontend (Next.js 14, Tailwind CSS v3, GSAP) based on the "Reserve Noir" (Midnight Luxe) design system. This app integrates with the FastAPI WebSocket endpoint (`ws://localhost:8000/api/v1/ws/kitchen`) to display incoming orders in real-time, allowing kitchen staff to transition order states (`pending` -> `preparing` -> `ready`) and clear tickets.

---

## User Review Required

> [!IMPORTANT]
> Please review the structure for the Chef Dashboard below. It will follow the "Midnight Luxe" aesthetic, modified slightly for high-throughput visibility (larger cards, stark contrast, persistent connection states).
> 
> A key workflow note: Kitchen staff will use the standard [AuthProvider](file:///d:/code/Project/tablez-demo2-allByAi/frontend/apps/reception-dashboard/src/components/AuthProvider.tsx#22-120) logic to authenticate as an admin/staff user, then the dashboard will upgrade the connection to WebSockets to stream live ticket updates.
> 
> Provide approval to move to EXECUTION mode.

---

## Proposed Changes

### 1. Global Setup
#### [MODIFY] [frontend/apps/chef-dashboard/src/app/globals.css](file:///d:/code/Project/tablez-demo2-allByAi/frontend/apps/chef-dashboard/src/app/globals.css) & [tailwind.config.ts](file:///d:/code/Project/tablez-demo2-allByAi/frontend/apps/chef-dashboard/tailwind.config.ts)
- Implement Midnight Luxe color tokens and noise overlays.
- Add specific status colors: Pending (Primary Gold), Preparing (Plasma Blue/Purple), Ready (Emerald Green).

### 2. Authentication & Data Fetching
#### [NEW] [frontend/apps/chef-dashboard/src/components/AuthProvider.tsx](file:///d:/code/Project/tablez-demo2-allByAi/frontend/apps/chef-dashboard/src/components/AuthProvider.tsx)
- Replicate the robust AuthProvider from the Reception App to secure the root view and provide the JWT token.
- [useApi](file:///d:/code/Project/tablez-demo2-allByAi/frontend/apps/reception-dashboard/src/lib/api.ts#6-37) hook to handle REST fallbacks (marking orders complete).

### 3. Real-Time Integration
#### [NEW] [frontend/apps/chef-dashboard/src/hooks/useWebSocket.ts](file:///d:/code/Project/tablez-demo2-allByAi/frontend/apps/chef-dashboard/src/hooks/useWebSocket.ts)
- Custom React hook managing the raw WebSocket connection to `/api/v1/ws/{restaurant_id}?token={jwt}`.
- Handles connection state (Connected, Disconnected, Reconnecting) and buffers incoming messages (`ORDER_CREATED`, `ORDER_UPDATED`).

### 4. Application Views
#### [NEW] [frontend/apps/chef-dashboard/src/app/login/page.tsx](file:///d:/code/Project/tablez-demo2-allByAi/frontend/apps/chef-dashboard/src/app/login/page.tsx)
- Auth login screen adapted for kitchen displays.
  
#### [NEW] [frontend/apps/chef-dashboard/src/app/page.tsx](file:///d:/code/Project/tablez-demo2-allByAi/frontend/apps/chef-dashboard/src/app/page.tsx)
- The main Kanban/Ticket Board.
- Displays incoming order "Tickets" with Tonal Stacking.
- **Micro-Interaction:** Swiping or clicking "Start" moves a ticket to Preparing. Clicking "Call" moves it to Ready.
- **WebSocket Status Indicator:** A pulsing orb top-right ensuring the kitchen knows the connection to the POS is live.

---

## Verification Plan
1. Start backend server with WebSockets enabled.
2. Build and run the `chef-dashboard` app.
3. Login using demo restaurant credentials.
4. Verify the WebSocket establishes a green `CONNECTED` status.
5. Emulate an order from the Customer App or via cURL and observe the Chef Dashboard rendering the incoming ticket *without* a hard refresh.
6. Verify status transitions update via the FASTAPI endpoint correctly.
