import { create } from "zustand";
import { devtools } from "zustand/middleware";

export interface Gateway {
  id: string;
  name: string;
  type: "CTP" | "SOPT";
  status: "HEALTHY" | "UNHEALTHY" | "STARTING" | "STOPPED";
  priority: number;
  isEnabled: boolean;
  lastHeartbeat: Date | null;
  connectionInfo: {
    host: string;
    port: number;
    connected: boolean;
  };
}

export interface GatewayState {
  gateways: Gateway[];
  selectedGateway: Gateway | null;

  // Actions
  setGateways: (gateways: Gateway[]) => void;
  updateGateway: (id: string, updates: Partial<Gateway>) => void;
  selectGateway: (gateway: Gateway | null) => void;
  addGateway: (gateway: Gateway) => void;
  removeGateway: (id: string) => void;
}

export const useGatewayStore = create<GatewayState>()(
  devtools(
    (set) => ({
      // Initial state
      gateways: [],
      selectedGateway: null,

      // Actions
      setGateways: (gateways) =>
        set((state) => ({ ...state, gateways }), false, "setGateways"),

      updateGateway: (id, updates) =>
        set(
          (state) => ({
            ...state,
            gateways: state.gateways.map((gateway) =>
              gateway.id === id ? { ...gateway, ...updates } : gateway,
            ),
          }),
          false,
          "updateGateway",
        ),

      selectGateway: (gateway) =>
        set(
          (state) => ({ ...state, selectedGateway: gateway }),
          false,
          "selectGateway",
        ),

      addGateway: (gateway) =>
        set(
          (state) => ({ ...state, gateways: [...state.gateways, gateway] }),
          false,
          "addGateway",
        ),

      removeGateway: (id) =>
        set(
          (state) => ({
            ...state,
            gateways: state.gateways.filter((gateway) => gateway.id !== id),
            selectedGateway:
              state.selectedGateway?.id === id ? null : state.selectedGateway,
          }),
          false,
          "removeGateway",
        ),
    }),
    {
      name: "gateway-store",
    },
  ),
);
