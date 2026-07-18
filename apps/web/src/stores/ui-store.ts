import { create } from "zustand";
import type { CitationSource } from "../api/types";

type SourcePanelState = {
  open: boolean;
  sources: CitationSource[];
  title: string;
  openSources: (sources: CitationSource[], title?: string) => void;
  close: () => void;
};

export const useSourcePanel = create<SourcePanelState>((set) => ({
  open: false,
  sources: [],
  title: "引用溯源",
  openSources: (sources, title = "引用溯源") =>
    set({ open: true, sources, title }),
  close: () => set({ open: false }),
}));
